import os
import random
import string

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

CATEGORY_LABELS = {
    "movie": "영화",
    "food": "맛집",
    "activity": "액티비티",
}

VALID_MAX_MEMBERS = (5, 10, 20, 50, 100)


def generate_group_code(length: int = 6) -> str:
    """그룹 코드를 만들고, 이미 쓰이는 코드와 겹치지 않을 때까지 재시도한다."""
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choices(alphabet, k=length))
        existing = supabase.table("groups").select("id").eq("code", code).execute()
        if not existing.data:
            return code


def get_group_by_code(code: str):
    res = supabase.table("groups").select("*").eq("code", code.upper()).execute()
    return res.data[0] if res.data else None


def get_group_by_id(group_id: str):
    res = supabase.table("groups").select("*").eq("id", group_id).execute()
    return res.data[0] if res.data else None


def count_members(group_id: str) -> int:
    res = supabase.table("members").select("id", count="exact").eq("group_id", group_id).execute()
    return res.count or 0


def get_member_by_token(device_token: str):
    res = supabase.table("members").select("*").eq("device_token", device_token).execute()
    return res.data[0] if res.data else None


def get_member_by_id(member_id: str):
    res = supabase.table("members").select("*").eq("id", member_id).execute()
    return res.data[0] if res.data else None


def get_reviews_with_location(group_id: str):
    """위도/경도가 채워진 리뷰만 지도용으로 조회."""
    res = (
        supabase.table("reviews")
        .select("*, members(nickname)")
        .eq("group_id", group_id)
        .not_.is_("latitude", "null")
        .not_.is_("longitude", "null")
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


def get_likes_for_reviews(review_ids: list):
    if not review_ids:
        return []
    res = supabase.table("likes").select("review_id, member_id").in_("review_id", review_ids).execute()
    return res.data


def get_comment_counts_for_reviews(review_ids: list) -> dict:
    if not review_ids:
        return {}
    res = supabase.table("comments").select("review_id").in_("review_id", review_ids).execute()
    counts: dict = {}
    for row in res.data:
        counts[row["review_id"]] = counts.get(row["review_id"], 0) + 1
    return counts


def get_review_by_id(review_id: str):
    res = supabase.table("reviews").select("*, members(nickname)").eq("id", review_id).execute()
    return res.data[0] if res.data else None


def get_comments_for_review(review_id: str):
    res = (
        supabase.table("comments")
        .select("*, members(nickname)")
        .eq("review_id", review_id)
        .order("created_at", desc=False)
        .execute()
    )
    return res.data


def toggle_like(review_id: str, member_id: str) -> bool:
    """좋아요를 누르면 True(추가됨), 다시 누르면 False(취소됨) 반환."""
    existing = (
        supabase.table("likes")
        .select("id")
        .eq("review_id", review_id)
        .eq("member_id", member_id)
        .execute()
    )
    if existing.data:
        supabase.table("likes").delete().eq("id", existing.data[0]["id"]).execute()
        return False
    supabase.table("likes").insert({"review_id": review_id, "member_id": member_id}).execute()
    return True


def add_comment(review_id: str, member_id: str, content: str):
    supabase.table("comments").insert(
        {"review_id": review_id, "member_id": member_id, "content": content}
    ).execute()
