"""달력 화면용 날짜 계산 모듈 (DB 없이도 테스트 가능한 순수 파이썬)."""
import calendar as pycal
from datetime import date, datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
WEEKDAYS_KO = ["월", "화", "수", "목", "금", "토", "일"]


def today_kst() -> date:
    """서버가 해외에 있어도 한국 날짜 기준으로 '오늘'을 계산한다."""
    return datetime.now(KST).date()


def parse_month(month_str: str, today: date) -> date:
    """'2026-10' 같은 문자열을 그 달 1일로 바꾼다. 잘못된 값이면 이번 달."""
    try:
        year, month = month_str.split("-")
        return date(int(year), int(month), 1)
    except (ValueError, AttributeError):
        return date(today.year, today.month, 1)


def parse_date(date_str: str):
    try:
        return date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


def shift_month(first: date, delta: int) -> date:
    index = first.year * 12 + (first.month - 1) + delta
    return date(index // 12, index % 12 + 1, 1)


def month_weeks(first: date):
    """일요일부터 시작하는 주 단위 날짜 목록 (앞뒤 달 날짜 포함)."""
    return pycal.Calendar(firstweekday=6).monthdatescalendar(first.year, first.month)


def pick_selected(first: date, requested, today: date) -> date:
    """선택된 날짜 결정: 요청값 > 오늘(이번 달일 때) > 그 달 1일."""
    if requested and (requested.year, requested.month) == (first.year, first.month):
        return requested
    if (today.year, today.month) == (first.year, first.month):
        return today
    return first


def build_weeks(weeks_dates, first: date, today: date, selected: date, by_date: dict):
    weeks = []
    for week in weeks_dates:
        row = []
        for d in week:
            iso = d.isoformat()
            row.append(
                {
                    "iso": iso,
                    "month_key": iso[:7],
                    "day": d.day,
                    "in_month": d.month == first.month,
                    "is_today": d == today,
                    "is_selected": d == selected,
                    "meetups": by_date.get(iso, []),
                }
            )
        weeks.append(row)
    return weeks


def date_label(d: date) -> str:
    return f"{d.month}월 {d.day}일 ({WEEKDAYS_KO[d.weekday()]})"


def parse_time_10min(hour_str, minute_str):
    """'시'와 '분' 문자열을 'HH:MM'으로 합친다. 분이 10분 단위가 아니거나 범위를 벗어나면 None."""
    try:
        hour = int(hour_str)
        minute = int(minute_str)
    except (ValueError, TypeError):
        return None
    if not (0 <= hour <= 23) or minute not in (0, 10, 20, 30, 40, 50):
        return None
    return f"{hour:02d}:{minute:02d}"
