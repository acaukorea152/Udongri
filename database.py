import os
import random
import string
import logging
import time
from functools import wraps

import httpx

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
logger = logging.getLogger(__name__)


def retry_transient_read(function):
    """Retry read-only Supabase queries after a brief network transport failure."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        for attempt in range(3):
            try:
                return function(*args, **kwargs)
            except httpx.TransportError:
                if attempt == 2:
                    raise
                delay = 0.25 * (2 ** attempt)
                logger.warning("Temporary Supabase read failure in %s; retrying", function.__name__)
                time.sleep(delay)
    return wrapped

CATEGORY_LABELS = {
    "movie": "영화",
    "food": "맛집",
    "activity": "액티비티",
}

VALID_MAX_MEMBERS = (5, 10, 20, 50, 100)


# ---------- 그룹 / 멤버 ----------

@retry_transient_read
def generate_group_code(length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choices(alphabet, k=length))
        existing = supabase.table("groups").select("id").eq("code", code).execute()
        if not existing.data:
            return code


@retry_transient_read
def get_group_by_code(code: str):
    res = supabase.table("groups").select("*").eq("code", code.upper()).execute()
    return res.data[0] if res.data else None


@retry_transient_read
def get_group_by_id(group_id: str):
    res = supabase.table("groups").select("*").eq("id", group_id).execute()
    return res.data[0] if res.data else None


# 모든 사람이 들어가는 단 하나의 공용 그룹
DEFAULT_GROUP_CODE = "UDONGRI"
DEFAULT_GROUP_TITLE = "우동리"


def get_or_create_default_group():
    """공용 그룹이 있으면 가져오고, 없으면 처음 한 번만 만든다."""
    group = get_group_by_code(DEFAULT_GROUP_CODE)
    if group:
        return group
    res = (
        supabase.table("groups")
        .insert({"title": DEFAULT_GROUP_TITLE, "code": DEFAULT_GROUP_CODE, "max_members": 100})
        .execute()
    )
    return res.data[0]


@retry_transient_read
def count_members(group_id: str) -> int:
    res = supabase.table("members").select("id", count="exact").eq("group_id", group_id).execute()
    return res.count or 0


@retry_transient_read
def get_member_by_token(device_token: str):
    res = supabase.table("members").select("*").eq("device_token", device_token).execute()
    return res.data[0] if res.data else None


@retry_transient_read
def get_member_by_id(member_id: str):
    res = supabase.table("members").select("*").eq("id", member_id).execute()
    return res.data[0] if res.data else None


# ---------- 리뷰 / 지도 / 좋아요 ----------

@retry_transient_read
def get_reviews_with_location(group_id: str):
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


@retry_transient_read
def get_likes_for_reviews(review_ids: list):
    if not review_ids:
        return []
    res = supabase.table("likes").select("review_id, member_id").in_("review_id", review_ids).execute()
    return res.data


@retry_transient_read
def get_review_by_id(review_id: str):
    res = supabase.table("reviews").select("*, members(nickname)").eq("id", review_id).execute()
    return res.data[0] if res.data else None


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


# ---------- 캘린더 (모임 모집) ----------

@retry_transient_read
def get_meetups_in_range(group_id: str, start_date: str, end_date: str):
    """화면에 보이는 달력 범위(start~end) 안의 모임을 날짜/시간순으로 가져온다."""
    res = (
        supabase.table("meetups")
        .select("*, members(nickname)")
        .eq("group_id", group_id)
        .gte("event_date", start_date)
        .lte("event_date", end_date)
        .order("event_date", desc=False)
        .order("event_time", desc=False)
        .execute()
    )
    return res.data


@retry_transient_read
def get_meetup_by_id(meetup_id: str):
    res = supabase.table("meetups").select("*, members(nickname)").eq("id", meetup_id).execute()
    return res.data[0] if res.data else None


def create_meetup(group_id: str, creator_member_id: str, title: str, event_date: str, event_time: str, max_people: int):
    res = (
        supabase.table("meetups")
        .insert(
            {
                "group_id": group_id,
                "creator_member_id": creator_member_id,
                "title": title,
                "event_date": event_date,
                "event_time": event_time,
                "max_people": max_people,
                "current_people": 1,  # 만든 사람 본인 1명으로 시작
            }
        )
        .execute()
    )
    return res.data[0]


def update_current_people(meetup_id: str, value: int):
    supabase.table("meetups").update({"current_people": value}).eq("id", meetup_id).execute()


def update_meetup(meetup_id: str, title: str, event_date: str, event_time: str, max_people: int):
    supabase.table("meetups").update(
        {
            "title": title,
            "event_date": event_date,
            "event_time": event_time,
            "max_people": max_people,
        }
    ).eq("id", meetup_id).execute()


def delete_meetup(meetup_id: str):
    """모임을 지우면 그 모임의 대화(meetup_comments)도 함께 지워진다."""
    supabase.table("meetups").delete().eq("id", meetup_id).execute()


@retry_transient_read
def get_meetup_comments(meetup_id: str):
    res = (
        supabase.table("meetup_comments")
        .select("*, members(nickname)")
        .eq("meetup_id", meetup_id)
        .order("created_at", desc=False)
        .execute()
    )
    return res.data


def add_meetup_comment(meetup_id: str, member_id: str, content: str):
    supabase.table("meetup_comments").insert(
        {"meetup_id": meetup_id, "member_id": member_id, "content": content}
    ).execute()
