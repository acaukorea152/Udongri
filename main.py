import json
import os
import uuid

from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

import calendar_utils as cu

from database import (
    supabase,
    SUPABASE_URL,
    SUPABASE_KEY,
    CATEGORY_LABELS,
    get_or_create_default_group,
    get_group_by_id,
    count_members,
    get_member_by_token,
    get_reviews_with_location,
    get_likes_for_reviews,
    get_review_by_id,
    toggle_like,
    get_meetups_in_range,
    get_meetup_by_id,
    create_meetup,
    update_current_people,
    get_meetup_comments,
    add_meetup_comment,
)

COOKIE_NAME = os.environ.get("SESSION_COOKIE_NAME", "udongri_token")
KAKAO_JS_KEY = os.environ.get("KAKAO_JS_KEY", "")

app = FastAPI(title="우동리")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def _tojson(value):
    raw = json.dumps(value, ensure_ascii=False).replace("</", "<\\/")
    return Markup(raw)  # Jinja2 자동 이스케이프로 JSON이 깨지지 않도록 안전 표시


templates.env.filters["tojson"] = _tojson


def current_member(request: Request):
    """쿠키의 device_token으로 현재 접속자가 누구인지 찾는다. 없으면 None."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return get_member_by_token(token)


# ---------- 시작 화면 (닉네임만 입력해서 공용 그룹으로 입장) ----------

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    group = get_or_create_default_group()
    member = current_member(request)
    if member and member["group_id"] == group["id"]:
        return RedirectResponse(url=f"/group/{group['id']}/calendar")
    return templates.TemplateResponse("start.html", {"request": request, "error": None})


@app.post("/enter", response_class=HTMLResponse)
def enter(request: Request, nickname: str = Form(...)):
    group = get_or_create_default_group()
    nickname = nickname.strip()

    error = None
    if not (1 <= len(nickname) <= 12):
        error = "닉네임은 1~12자로 입력해주세요."
    elif count_members(group["id"]) >= group["max_members"]:
        error = "정원이 가득 찼어요."

    if error:
        return templates.TemplateResponse(
            "start.html", {"request": request, "error": error}, status_code=400
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

    response = RedirectResponse(url=f"/group/{group['id']}/calendar", status_code=303)
    response.set_cookie(COOKIE_NAME, device_token, max_age=60 * 60 * 24 * 365, httponly=True)
    return response


# ---------- 캘린더 (모임 모집) : 기본 홈 화면 ----------

@app.get("/group/{group_id}/calendar", response_class=HTMLResponse)
def calendar_view(
    request: Request,
    group_id: str,
    month: str = "",
    selected_date: str = Query("", alias="date"),
):
    member = current_member(request)
    if not member or member["group_id"] != group_id:
        return RedirectResponse(url="/")

    group = get_group_by_id(group_id)
    today = cu.today_kst()
    first = cu.parse_month(month, today)
    weeks_dates = cu.month_weeks(first)
    selected = cu.pick_selected(first, cu.parse_date(selected_date), today)

    # 달력에 보이는 범위(앞뒤 달 날짜 포함)의 모임만 가져온다
    range_start = weeks_dates[0][0].isoformat()
    range_end = weeks_dates[-1][-1].isoformat()
    meetups = get_meetups_in_range(group_id, range_start, range_end)

    by_date: dict = {}
    for item in meetups:
        item["is_full"] = item["current_people"] >= item["max_people"]
        item["is_mine"] = item["creator_member_id"] == member["id"]
        by_date.setdefault(item["event_date"], []).append(item)

    weeks = cu.build_weeks(weeks_dates, first, today, selected, by_date)
    selected_iso = selected.isoformat()
    calendar_url = f"/group/{group_id}/calendar?month={first.strftime('%Y-%m')}&date={selected_iso}"

    return templates.TemplateResponse(
        "calendar.html",
        {
            "request": request,
            "group": group,
            "active_tab": "calendar",
            "member": member,
            "year": first.year,
            "month_number": first.month,
            "prev_month": cu.shift_month(first, -1).strftime("%Y-%m"),
            "next_month": cu.shift_month(first, 1).strftime("%Y-%m"),
            "weeks": weeks,
            "selected_iso": selected_iso,
            "selected_label": cu.date_label(selected),
            "selected_meetups": by_date.get(selected_iso, []),
            "calendar_url": calendar_url,
            "supabase_url": SUPABASE_URL,
            "supabase_anon_key": SUPABASE_KEY,
        },
    )


@app.get("/group/{group_id}/calendar/new", response_class=HTMLResponse)
def new_meetup_form(request: Request, group_id: str, prefill_date: str = Query("", alias="date")):
    member = current_member(request)
    if not member or member["group_id"] != group_id:
        return RedirectResponse(url="/")

    group = get_group_by_id(group_id)
    parsed = cu.parse_date(prefill_date)
    return templates.TemplateResponse(
        "meetup_new.html",
        {
            "request": request,
            "group": group,
            "active_tab": "calendar",
            "error": None,
            "form": {
                "title": "",
                "event_date": parsed.isoformat() if parsed else "",
                "event_hour": "",
                "event_minute": "",
                "max_people": 4,
            },
        },
    )


@app.post("/group/{group_id}/calendar/new", response_class=HTMLResponse)
def new_meetup_submit(
    request: Request,
    group_id: str,
    title: str = Form(...),
    event_date: str = Form(...),
    event_hour: str = Form(""),
    event_minute: str = Form(""),
    max_people: int = Form(...),
):
    member = current_member(request)
    if not member or member["group_id"] != group_id:
        return RedirectResponse(url="/")

    group = get_group_by_id(group_id)
    title = title.strip()
    event_time = cu.parse_time_10min(event_hour, event_minute)  # 'HH:MM' 또는 None
    error = None

    if not (1 <= len(title) <= 30):
        error = "모임 제목은 1~30자로 입력해주세요."
    elif not cu.parse_date(event_date):
        error = "날짜를 선택해주세요."
    elif not event_time:
        error = "시간을 10분 단위로 선택해주세요."
    elif not (1 <= max_people <= 100):
        error = "모집 인원은 1~100 사이로 입력해주세요."

    if error:
        return templates.TemplateResponse(
            "meetup_new.html",
            {
                "request": request,
                "group": group,
                "active_tab": "calendar",
                "error": error,
                "form": {
                    "title": title,
                    "event_date": event_date,
                    "event_hour": event_hour,
                    "event_minute": event_minute,
                    "max_people": max_people,
                },
            },
            status_code=400,
        )

    create_meetup(group_id, member["id"], title, event_date, event_time, max_people)
    # 만든 날짜가 보이는 달력으로 돌아간다
    return RedirectResponse(
        url=f"/group/{group_id}/calendar?month={event_date[:7]}&date={event_date}",
        status_code=303,
    )


@app.post("/meetup/{meetup_id}/adjust")
def adjust_meetup(
    request: Request,
    meetup_id: str,
    delta: int = Form(...),
    next: str = Form(""),
):
    """작성자만 현재 모인 인원을 1명씩 늘리거나 줄일 수 있다."""
    meetup = get_meetup_by_id(meetup_id)
    if not meetup:
        return RedirectResponse(url="/")

    member = current_member(request)
    if not member or member["group_id"] != meetup["group_id"]:
        return RedirectResponse(url="/")

    if member["id"] == meetup["creator_member_id"] and delta in (-1, 1):
        new_value = max(0, min(meetup["max_people"], meetup["current_people"] + delta))
        update_current_people(meetup_id, new_value)

    # 우리 사이트 안의 주소로만 돌아가도록 제한
    if next.startswith("/group/") or next.startswith("/meetup/"):
        return RedirectResponse(url=next, status_code=303)
    return RedirectResponse(url=f"/group/{meetup['group_id']}/calendar", status_code=303)


@app.get("/meetup/{meetup_id}", response_class=HTMLResponse)
def meetup_detail(request: Request, meetup_id: str):
    meetup = get_meetup_by_id(meetup_id)
    if not meetup:
        return RedirectResponse(url="/")

    member = current_member(request)
    if not member or member["group_id"] != meetup["group_id"]:
        return RedirectResponse(url="/")

    group = get_group_by_id(meetup["group_id"])
    meetup["is_full"] = meetup["current_people"] >= meetup["max_people"]
    meetup["is_mine"] = meetup["creator_member_id"] == member["id"]
    comments = get_meetup_comments(meetup_id)

    return templates.TemplateResponse(
        "meetup_detail.html",
        {
            "request": request,
            "group": group,
            "active_tab": "calendar",
            "meetup": meetup,
            "comments": comments,
            "back_url": f"/group/{group['id']}/calendar?month={meetup['event_date'][:7]}&date={meetup['event_date']}",
            "supabase_url": SUPABASE_URL,
            "supabase_anon_key": SUPABASE_KEY,
        },
    )


@app.post("/meetup/{meetup_id}/comment")
def meetup_comment_submit(request: Request, meetup_id: str, content: str = Form(...)):
    meetup = get_meetup_by_id(meetup_id)
    if not meetup:
        return RedirectResponse(url="/")

    member = current_member(request)
    if not member or member["group_id"] != meetup["group_id"]:
        return RedirectResponse(url="/")

    content = content.strip()
    if content:
        add_meetup_comment(meetup_id, member["id"], content)

    return RedirectResponse(url=f"/meetup/{meetup_id}", status_code=303)


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

    for r in reviews:
        r["like_count"] = like_counts.get(r["id"], 0)
        r["liked_by_me"] = r["id"] in my_likes

    return templates.TemplateResponse(
        "board.html",
        {
            "request": request,
            "group": group,
            "active_tab": "board",
            "member": member,
            "reviews": reviews,
            "category_labels": CATEGORY_LABELS,
            "supabase_url": SUPABASE_URL,
            "supabase_anon_key": SUPABASE_KEY,
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


# ---------- 리뷰 상세 (댓글 없음, 좋아요만) ----------

@app.get("/review/{review_id}", response_class=HTMLResponse)
def review_detail(request: Request, review_id: str):
    review = get_review_by_id(review_id)
    if not review:
        return RedirectResponse(url="/")

    member = current_member(request)
    if not member or member["group_id"] != review["group_id"]:
        return RedirectResponse(url="/")

    group = get_group_by_id(review["group_id"])

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


# ---------- 로그아웃 (다른 그룹으로 테스트할 때 사용) ----------

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie(COOKIE_NAME)
    return response
