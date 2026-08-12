-- Chay trong Supabase SQL Editor sau 001_init.sql
-- Can cho che do webhook (Vercel). Che do polling khong dung bang nay.

-- Telegram gui lai update neu webhook phan hoi cham (agent mat 20-60s), nen phai
-- chan xu ly trung - neu khong ban se nhan 2 cau tra loi cho 1 tin nhan.
create table if not exists processed_updates (
  update_id bigint primary key,
  processed_at timestamptz not null default now()
);

-- Don ban ghi cu de bang khong phinh mai
create index if not exists idx_processed_updates_time on processed_updates(processed_at);
