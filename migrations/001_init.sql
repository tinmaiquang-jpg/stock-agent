-- Chay file nay trong Supabase SQL Editor (Project > SQL Editor > New query)

create table if not exists app_config (
  key text primary key,
  value text not null,
  updated_at timestamptz not null default now()
);

insert into app_config (key, value) values
  ('system_prompt', 'Ban la tro ly ca nhan theo doi va phan tich chung khoan Viet Nam cho chinh chu. Dung cac tool duoc cung cap de lay du lieu thuc te truoc khi tra loi - khong bao gio doan gia. Chi cung cap thong tin, phan tich va canh bao - KHONG dat lenh mua/ban thuc te va khong dua ra loi khuyen dau tu mang tinh chat tu van tai chinh chuyen nghiep. Tra loi ngan gon, ro rang, bang tieng Viet. Gia co phieu tra ve tu tool co don vi nghin VND.'),
  -- Sonnet 5: can bang tot nhat cho use case nay. Haiku 4.5 re hon nhung yeu hon o
  -- tool-use nhieu buoc va khong dat nguong prompt caching (can >= 4096 token prefix,
  -- prefix cua app nay ~1050). Doi model bat cu luc nao tren web admin.
  ('model', 'claude-sonnet-5'),
  ('effort', 'medium'),
  ('max_history_messages', '20'),
  -- 'subscription' = Claude Agent SDK + CLAUDE_CODE_OAUTH_TOKEN (goi Pro/Max, khong ton
  -- tien API). 'api_key' = Messages API + CLAUDE_API_KEY (tinh tien theo token).
  ('llm_backend', 'subscription')
on conflict (key) do nothing;

create table if not exists conversations (
  id bigserial primary key,
  telegram_user_id bigint not null,
  created_at timestamptz not null default now()
);
create index if not exists idx_conversations_user on conversations(telegram_user_id);

create table if not exists messages (
  id bigserial primary key,
  conversation_id bigint not null references conversations(id) on delete cascade,
  role text not null check (role in ('user','assistant')),
  content text not null,
  created_at timestamptz not null default now()
);
create index if not exists idx_messages_conversation on messages(conversation_id, created_at);

create table if not exists watchlist (
  id bigserial primary key,
  ticker text not null unique,
  note text,
  created_at timestamptz not null default now()
);

create table if not exists alerts (
  id bigserial primary key,
  ticker text not null,
  condition text not null check (condition in ('price_above','price_below','pct_change')),
  threshold numeric not null,
  active boolean not null default true,
  last_triggered_at timestamptz,
  created_at timestamptz not null default now()
);
create index if not exists idx_alerts_active on alerts(active);

create table if not exists alert_log (
  id bigserial primary key,
  alert_id bigint not null references alerts(id) on delete cascade,
  triggered_at timestamptz not null default now(),
  price_at_trigger numeric,
  message_sent text
);

-- Danh cho key broker tuong lai (chua dung o giai doan hien tai). Gia tri luon
-- duoc ma hoa (Fernet) o phia app truoc khi luu - khong bao gio luu plaintext.
create table if not exists secrets (
  key text primary key,
  encrypted_value text not null,
  created_at timestamptz not null default now()
);
