-- 캘린더 개편용: 모임마다 '현재 모인 인원'을 저장하는 칸 추가
-- Supabase SQL Editor에서 한 번만 실행하세요.
alter table meetups
  add column if not exists current_people integer not null default 1
  check (current_people >= 0);
