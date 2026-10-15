-- 우동리 기본 스키마 (Sprint 1~3). 이미 실행하셨다면 다시 실행하지 않아도 됩니다.
create extension if not exists "pgcrypto";

create table if not exists groups (
  id uuid primary key default gen_random_uuid(),
  title text not null check (char_length(title) <= 12),
  code text unique not null,
  max_members integer not null check (max_members in (5,10,20,50,100)),
  created_at timestamptz not null default now()
);

create table if not exists members (
  id uuid primary key default gen_random_uuid(),
  group_id uuid not null references groups(id) on delete cascade,
  nickname text not null check (char_length(nickname) <= 12),
  is_owner boolean not null default false,
  device_token text not null unique,
  joined_at timestamptz not null default now()
);

create table if not exists reviews (
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

create table if not exists likes (
  id uuid primary key default gen_random_uuid(),
  review_id uuid not null references reviews(id) on delete cascade,
  member_id uuid not null references members(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (review_id, member_id)
);

-- comments 테이블은 리뷰 댓글 기능 제거로 더 이상 쓰지 않습니다 (남아있어도 무방).
create table if not exists comments (
  id uuid primary key default gen_random_uuid(),
  review_id uuid not null references reviews(id) on delete cascade,
  member_id uuid not null references members(id) on delete cascade,
  content text not null,
  created_at timestamptz not null default now()
);

alter table groups enable row level security;
alter table members enable row level security;
alter table reviews enable row level security;
alter table likes enable row level security;
alter table comments enable row level security;

create policy if not exists "public all groups" on groups for all using (true) with check (true);
create policy if not exists "public all members" on members for all using (true) with check (true);
create policy if not exists "public all reviews" on reviews for all using (true) with check (true);
create policy if not exists "public all likes" on likes for all using (true) with check (true);
create policy if not exists "public all comments" on comments for all using (true) with check (true);
