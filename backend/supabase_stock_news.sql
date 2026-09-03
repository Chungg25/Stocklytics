-- Run this script in your Supabase SQL Editor

CREATE TABLE IF NOT EXISTS stock_news (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticker VARCHAR(10) NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    source VARCHAR(255),
    summary TEXT,
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(url)
);

-- Index for fast lookup by ticker
CREATE INDEX IF NOT EXISTS idx_stock_news_ticker ON stock_news(ticker);

-- Enable RLS
ALTER TABLE stock_news ENABLE ROW LEVEL SECURITY;

-- Allow public read access to news
CREATE POLICY "Public can view stock news" ON stock_news
    FOR SELECT USING (true);

-- Allow service role to insert
CREATE POLICY "Service role can manage stock news" ON stock_news
    USING (true)
    WITH CHECK (true);
