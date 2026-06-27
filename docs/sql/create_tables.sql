create table contracts (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  description text not null default '',
  allowed_tools text[] not null,
  created_at timestamptz not null default now()
);
