-- Chay trong Supabase SQL Editor sau 002_webhook.sql
-- Cache lich su gia de screener khong dam vao gioi han 20 request/phut cua vnstock
-- (quet VN30 can 30 request). Du lieu OHLCV theo ngay khong doi trong phien nen cache
-- 1 lan/ngay/ma la du.

create table if not exists ohlcv_cache (
  symbol text primary key,
  data jsonb not null,
  fetched_date date not null,
  updated_at timestamptz not null default now()
);

create index if not exists idx_ohlcv_cache_date on ohlcv_cache(fetched_date);
