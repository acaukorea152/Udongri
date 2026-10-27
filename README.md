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

## 휴대폰에서 앱처럼 설치 (PWA)
- 배포된 사이트가 HTTPS로 열리면 앱스토어 없이 설치할 수 있습니다.
- Android: Chrome에서 사이트에 접속한 뒤 화면의 `설치` 버튼을 누르거나 브라우저 메뉴에서 `앱 설치`를 선택합니다.
- iPhone/iPad: Safari에서 사이트를 연 뒤 공유 버튼 → `홈 화면에 추가`를 선택합니다.
- 설치 후에도 일정, 게시글, 지도 등 서버 기능을 사용하려면 인터넷 연결이 필요합니다. 오프라인에서는 연결 안내 화면이 표시됩니다.
