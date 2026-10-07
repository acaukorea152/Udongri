-- 우동리(우리 동아리 리뷰) DB 스키마
-- Supabase SQL Editor에 전체 붙여넣고 Run

create extension if not exists "pgcrypto";

create table groups (
  id uuid primary key default gen_random_uuid(),
  title text not null check (char_length(title) <= 12),
  code text unique not null,
  max_members integer not null check (max_members in (5,10,20,50,100)),
  created_at timestamptz not null default now()
);

create table members (
  id uuid primary key default gen_random_uuid(),
  group_id uuid not null references groups(id) on delete cascade,
  nickname text not null check (char_length(nickname) <= 12),
  is_owner boolean not null default false,
  device_token text not null unique,
  joined_at timestamptz not null default now()
);

create table reviews (
  id uuid primary key default gen_random_uuid(),
  group_id uuid not null references groups(id) on delete cascade,
  author_member_id uuid not null references members(id) on delete cascade,
  category text not null check (category in ('movie','food','activity')),
  title text not null check (char_length(title) >= 1),
  content text,
  star_count integer not null default 0 check (star_count between 0 and 5),
  place_name text,
  latitude double precision,
  longitude double precision,
  created_at timestamptz not null default now()
);

create table likes (
  id uuid primary key default gen_random_uuid(),
  review_id uuid not null references reviews(id) on delete cascade,
  member_id uuid not null references members(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (review_id, member_id)
);

create table comments (
  id uuid primary key default gen_random_uuid(),
  review_id uuid not null references reviews(id) on delete cascade,
  member_id uuid not null references members(id) on delete cascade,
  content text not null,
  created_at timestamptz not null default now()
);

-- RLS: MVP 단계에서는 "그룹 코드/링크를 아는 사람만 접근"하는 수준으로 느슨하게 열어둠.
-- 나중에 강화 가능 (예: group_id를 아는 요청만 허용하는 정책으로 세분화).
alter table groups enable row level security;
alter table members enable row level security;
alter table reviews enable row level security;
alter table likes enable row level security;
alter table comments enable row level security;

create policy "public all groups" on groups for all using (true) with check (true);
create policy "public all members" on members for all using (true) with check (true);
create policy "public all reviews" on reviews for all using (true) with check (true);
create policy "public all likes" on likes for all using (true) with check (true);
create policy "public all comments" on comments for all using (true) with check (true);
