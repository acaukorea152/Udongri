-- 캘린더(모임 모집) 기능용 테이블
-- Supabase SQL Editor에서 실행

create table meetups (
  id uuid primary key default gen_random_uuid(),
  group_id uuid not null references groups(id) on delete cascade,
  creator_member_id uuid not null references members(id) on delete cascade,
  title text not null check (char_length(title) <= 30),
  event_date date not null,
  event_time time not null,
  max_people integer not null check (max_people between 1 and 100),
  created_at timestamptz not null default now()
);

create table meetup_participants (
  id uuid primary key default gen_random_uuid(),
  meetup_id uuid not null references meetups(id) on delete cascade,
  member_id uuid not null references members(id) on delete cascade,
  joined_at timestamptz not null default now(),
  unique (meetup_id, member_id)
);

create table meetup_comments (
  id uuid primary key default gen_random_uuid(),
  meetup_id uuid not null references meetups(id) on delete cascade,
  member_id uuid not null references members(id) on delete cascade,
  content text not null,
  created_at timestamptz not null default now()
);

alter table meetups enable row level security;
alter table meetup_participants enable row level security;
alter table meetup_comments enable row level security;

create policy "public all meetups" on meetups for all using (true) with check (true);
create policy "public all meetup_participants" on meetup_participants for all using (true) with check (true);
create policy "public all meetup_comments" on meetup_comments for all using (true) with check (true);

-- 실시간 업데이트 대상에도 추가
alter publication supabase_realtime add table meetups;
alter publication supabase_realtime add table meetup_participants;
alter publication supabase_realtime add table meetup_comments;
