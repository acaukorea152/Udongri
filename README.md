# 우동리 (우리 동아리 리뷰) — Sprint 1

Sprint 1 범위: 그룹 만들기/참가하기, 게시판(리뷰 목록), 리뷰 작성.
(지도, 좋아요, 댓글은 다음 스프린트에서 추가 예정)

## 1. Supabase 테이블 만들기

1. Supabase 프로젝트의 **SQL Editor** 를 연다.
2. `schema.sql` 파일 내용을 전체 복사해서 붙여넣고 **Run** 실행.

## 2. 로컬에서 실행해보기

Python 3.10 이상이 설치되어 있어야 합니다.

```bash
cd udongri
python3 -m venv venv
source venv/bin/activate   # Windows는: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

브라우저에서 http://127.0.0.1:8000 접속.

`.env` 파일에는 이미 본인의 Supabase URL/키가 들어있습니다.
(이 파일은 절대 깃허브 등에 공개로 올리지 마세요 — `.gitignore`에 포함해두었습니다.)

## 3. 테스트 방법

- 그룹 만들기로 그룹 하나 생성 → 게시판에서 리뷰 써보기
- 다른 브라우저(또는 시크릿 모드)를 열어 같은 그룹 코드로 참가 → 다른 사람인 척 리뷰 써보기
  (브라우저마다 별도 쿠키를 쓰므로 다른 멤버로 인식됩니다)
- `/logout` 접속하면 현재 브라우저의 로그인 정보가 지워져서 처음 화면으로 돌아갑니다

## 4. 다음 스프린트에서 할 일

- 지도 탭: 카카오맵 연동, 리뷰 작성 시 위치 선택
- 게시판에 좋아요(하트)/댓글
- 실시간 업데이트 (Supabase Realtime)
- Render.com 배포

## 배포 (Render.com, 무료)

1. 이 폴더를 GitHub 저장소로 올린다 (`.env`는 제외).
2. Render.com → New → Web Service → 저장소 연결.
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Environment 탭에서 `SUPABASE_URL`, `SUPABASE_KEY`, `SESSION_COOKIE_NAME`를 직접 입력 (여기서는 .env 파일이 안 쓰이고 Render의 환경변수 설정을 씁니다).
