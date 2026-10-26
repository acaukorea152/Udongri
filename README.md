# 우동리 (우리 동아리 리뷰)

- 접속하면 닉네임만 입력해서 공용 그룹(하나)으로 입장
- 캘린더(달력 + 모임 모집, 작성자가 현재 인원 조절/수정/삭제, 대화), 게시판(리뷰 + 좋아요), 지도, 리뷰 쓰기

## Supabase SQL Editor에서 실행 (한 번씩)
1. `calendar_schema.sql`  (캘린더 기본 테이블, 이미 실행했다면 생략)
2. `calendar_update.sql`  (현재 인원 칸 추가)

## 로컬 실행
```
venv\Scripts\activate
uvicorn main:app --reload
```
브라우저에서 http://localhost:8000 접속 (127.0.0.1 말고 localhost)

## 배포
git add .  /  git commit -m "메시지"  /  git push  → Render가 자동 재배포
