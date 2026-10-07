import json
import os
import uuid

from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from database import (
    supabase,
    CATEGORY_LABELS,
    VALID_MAX_MEMBERS,
    generate_group_code,
    get_group_by_code,
    get_group_by_id,
    count_members,
    get_member_by_token,
    get_reviews_with_location,
    get_likes_for_reviews,
    get_comment_counts_for_reviews,
    get_review_by_id,
    get_comments_for_review,
    toggle_like,
    add_comment,
)

COOKIE_NAME = os.environ.get("SESSION_COOKIE_NAME", "udongri_token")
KAKAO_JS_KEY = os.environ.get("KAKAO_JS_KEY", "")

app = FastAPI(title="우동리")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def _tojson(value):
    # </script> 로 스크립트가 끊기는 것도 함께 방지
    raw = json.dumps(value, ensure_ascii=False).replace("</", "<\\/")
    return Markup(raw)  # Jinja2 자동 이스케이프로 JSON이 깨지지 않도록 안전 표시


templates.env.filters["tojson"] = _tojson


def current_member(request: Request):
    """쿠키의 device_token으로 현재 접속자가 누구인지 찾는다. 없으면 None."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return get_member_by_token(token)


# ---------- 시작 화면 ----------

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    member = current_member(request)
    if member:
        return RedirectResponse(url=f"/group/{member['group_id']}/board")
    return templates.TemplateResponse("start.html", {"request": request, "error": None})


# ---------- 그룹 만들기 ----------

@app.get("/group/create", response_class=HTMLResponse)
def create_group_form(request: Request):
    return templates.TemplateResponse(
        "create_group.html",
        {"request": request, "max_options": VALID_MAX_MEMBERS, "error": None},
    )


@app.post("/group/create", response_class=HTMLResponse)
def create_group_submit(
    request: Request,
    title: str = Form(...),
    max_members: int = Form(...),
    nickname: str = Form(...),
):
    title = title.strip()
    nickname = nickname.strip()
    error = None
    if not (1 <= len(title) <= 12):
        error = "그룹 제목은 1~12자로 입력해주세요."
    elif not (1 <= len(nickname) <= 12):
        error = "닉네임은 1~12자로 입력해주세요."
    elif max_members not in VALID_MAX_MEMBERS:
        error = "최대 인원을 다시 선택해주세요."

    if error:
        return templates.TemplateResponse(
            "create_group.html",
            {"request": request, "max_options": VALID_MAX_MEMBERS, "error": error},
            status_code=400,
        )

    code = generate_group_code()
    device_token = str(uuid.uuid4())

    group_res = (
        supabase.table("groups")
        .insert({"title": title, "code": code, "max_members": max_members})
        .execute()
    )
    group = group_res.data[0]

    supabase.table("members").insert(
        {
            "group_id": group["id"],
            "nickname": nickname,
            "is_owner": True,
            "device_token": device_token,
        }
    ).execute()

    response = RedirectResponse(url=f"/group/{group['id']}/board", status_code=303)
    response.set_cookie(COOKIE_NAME, device_token, max_age=60 * 60 * 24 * 365, httponly=True)
    return response


# ---------- 그룹 참가하기 ----------

@app.get("/group/join", response_class=HTMLResponse)
def join_group_form(request: Request):
    return templates.TemplateResponse("join_group.html", {"request": request, "error": None})


@app.post("/group/join", response_class=HTMLResponse)
def join_group_submit(
    request: Request,
    code: str = Form(...),
    nickname: str = Form(...),
):
    code = code.strip().upper()
    nickname = nickname.strip()

    group = get_group_by_code(code)
    error = None
    if not group:
        error = "존재하지 않는 그룹 코드예요. 다시 확인해주세요."
    elif not (1 <= len(nickname) <= 12):
        error = "닉네임은 1~12자로 입력해주세요."
    elif count_members(group["id"]) >= group["max_members"]:
        error = "그룹 정원이 가득 찼어요."

    if error:
        return templates.TemplateResponse(
            "join_group.html", {"request": request, "error": error}, status_code=400
        )

    device_token = str(uuid.uuid4())
    supabase.table("members").insert(
        {
            "group_id": group["id"],
            "nickname": nickname,
            "is_owner": False,
            "device_token": device_token,
        }
    ).execute()

    response = RedirectResponse(url=f"/group/{group['id']}/board", status_code=303)
    response.set_cookie(COOKIE_NAME, device_token, max_age=60 * 60 * 24 * 365, httponly=True)
    return response


# ---------- 게시판 ----------

@app.get("/group/{group_id}/board", response_class=HTMLResponse)
def board(request: Request, group_id: str):
    member = current_member(request)
    if not member or member["group_id"] != group_id:
        return RedirectResponse(url="/")

    group = get_group_by_id(group_id)
    reviews_res = (
        supabase.table("reviews")
        .select("*, members(nickname)")
        .eq("group_id", group_id)
        .order("created_at", desc=True)
        .execute()
    )
    reviews = reviews_res.data
    review_ids = [r["id"] for r in reviews]

    likes = get_likes_for_reviews(review_ids)
    like_counts: dict = {}
    my_likes: set = set()
    for like in likes:
        like_counts[like["review_id"]] = like_counts.get(like["review_id"], 0) + 1
        if like["member_id"] == member["id"]:
            my_likes.add(like["review_id"])

    comment_counts = get_comment_counts_for_reviews(review_ids)

    for r in reviews:
        r["like_count"] = like_counts.get(r["id"], 0)
        r["liked_by_me"] = r["id"] in my_likes
        r["comment_count"] = comment_counts.get(r["id"], 0)

    return templates.TemplateResponse(
        "board.html",
        {
            "request": request,
            "group": group,
            "active_tab": "board",
            "member": member,
            "reviews": reviews,
            "category_labels": CATEGORY_LABELS,
        },
    )


# ---------- 지도 ----------

@app.get("/group/{group_id}/map", response_class=HTMLResponse)
def map_view(request: Request, group_id: str):
    member = current_member(request)
    if not member or member["group_id"] != group_id:
        return RedirectResponse(url="/")

    group = get_group_by_id(group_id)
    reviews = get_reviews_with_location(group_id)

    markers = [
        {
            "id": r["id"],
            "lat": r["latitude"],
            "lng": r["longitude"],
            "title": r["title"],
            "nickname": r["members"]["nickname"],
            "star_count": r["star_count"],
            "category": r["category"],
            "category_label": CATEGORY_LABELS.get(r["category"], r["category"]),
            "place_name": r.get("place_name") or "",
        }
        for r in reviews
    ]

    return templates.TemplateResponse(
        "map.html",
        {
            "request": request,
            "group": group,
            "active_tab": "map",
            "markers": markers,
            "kakao_js_key": KAKAO_JS_KEY,
        },
    )


# ---------- 리뷰 작성 ----------

@app.get("/group/{group_id}/write", response_class=HTMLResponse)
def write_review_form(request: Request, group_id: str):
    member = current_member(request)
    if not member or member["group_id"] != group_id:
        return RedirectResponse(url="/")

    group = get_group_by_id(group_id)
    return templates.TemplateResponse(
        "write_review.html",
        {
            "request": request,
            "group": group,
            "active_tab": "write",
            "category_labels": CATEGORY_LABELS,
            "kakao_js_key": KAKAO_JS_KEY,
            "error": None,
            "form": {
                "category": "movie",
                "star_count": 0,
                "title": "",
                "content": "",
                "place_name": "",
                "latitude": "",
                "longitude": "",
            },
        },
    )


@app.post("/group/{group_id}/write", response_class=HTMLResponse)
def write_review_submit(
    request: Request,
    group_id: str,
    category: str = Form(...),
    star_count: int = Form(0),
    title: str = Form(...),
    content: str = Form(""),
    place_name: str = Form(""),
    latitude: str = Form(""),
    longitude: str = Form(""),
):
    member = current_member(request)
    if not member or member["group_id"] != group_id:
        return RedirectResponse(url="/")

    group = get_group_by_id(group_id)
    title = title.strip()
    content = content.strip()
    place_name = place_name.strip()
    error = None

    if category not in CATEGORY_LABELS:
        error = "카테고리를 선택해주세요."
    elif not (0 <= star_count <= 5):
        error = "별점은 0~5 사이여야 해요."
    elif len(title) < 1:
        error = "리뷰 제목은 꼭 입력해주세요."

    form_state = {
        "category": category,
        "star_count": star_count,
        "title": title,
        "content": content,
        "place_name": place_name,
        "latitude": latitude,
        "longitude": longitude,
    }

    if error:
        return templates.TemplateResponse(
            "write_review.html",
            {
                "request": request,
                "group": group,
                "active_tab": "write",
                "category_labels": CATEGORY_LABELS,
                "kakao_js_key": KAKAO_JS_KEY,
                "error": error,
                "form": form_state,
            },
            status_code=400,
        )

    # 위치는 선택 사항이라, 값이 없거나 잘못된 숫자면 그냥 비워둔다.
    lat_value = None
    lng_value = None
    try:
        if latitude and longitude:
            lat_value = float(latitude)
            lng_value = float(longitude)
    except ValueError:
        lat_value = None
        lng_value = None

    supabase.table("reviews").insert(
        {
            "group_id": group_id,
            "author_member_id": member["id"],
            "category": category,
            "title": title,
            "content": content or None,
            "star_count": star_count,
            "place_name": place_name or None,
            "latitude": lat_value,
            "longitude": lng_value,
        }
    ).execute()

    return RedirectResponse(url=f"/group/{group_id}/board", status_code=303)


# ---------- 리뷰 상세 (댓글) ----------

@app.get("/review/{review_id}", response_class=HTMLResponse)
def review_detail(request: Request, review_id: str):
    review = get_review_by_id(review_id)
    if not review:
        return RedirectResponse(url="/")

    member = current_member(request)
    if not member or member["group_id"] != review["group_id"]:
        return RedirectResponse(url="/")

    group = get_group_by_id(review["group_id"])
    comments = get_comments_for_review(review_id)

    likes = get_likes_for_reviews([review_id])
    like_count = len(likes)
    liked_by_me = any(like["member_id"] == member["id"] for like in likes)

    return templates.TemplateResponse(
        "review_detail.html",
        {
            "request": request,
            "group": group,
            "active_tab": "board",
            "review": review,
            "comments": comments,
            "like_count": like_count,
            "liked_by_me": liked_by_me,
            "category_labels": CATEGORY_LABELS,
        },
    )


# ---------- 좋아요 토글 ----------

@app.post("/review/{review_id}/like")
def like_review(request: Request, review_id: str, next: str = Form("board")):
    review = get_review_by_id(review_id)
    if not review:
        return RedirectResponse(url="/")

    member = current_member(request)
    if not member or member["group_id"] != review["group_id"]:
        return RedirectResponse(url="/")

    toggle_like(review_id, member["id"])

    if next == "detail":
        return RedirectResponse(url=f"/review/{review_id}", status_code=303)
    return RedirectResponse(url=f"/group/{review['group_id']}/board", status_code=303)


# ---------- 댓글 작성 ----------

@app.post("/review/{review_id}/comment")
def comment_submit(request: Request, review_id: str, content: str = Form(...)):
    review = get_review_by_id(review_id)
    if not review:
        return RedirectResponse(url="/")

    member = current_member(request)
    if not member or member["group_id"] != review["group_id"]:
        return RedirectResponse(url="/")

    content = content.strip()
    if content:
        add_comment(review_id, member["id"], content)

    return RedirectResponse(url=f"/review/{review_id}", status_code=303)


# ---------- 로그아웃 (다른 그룹으로 테스트할 때 사용) ----------

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie(COOKIE_NAME)
    return response
