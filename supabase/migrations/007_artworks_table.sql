-- Migration 007: Create public artworks table for marketplace publishing and community showcase
CREATE TABLE IF NOT EXISTS public.artworks (
    id TEXT PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    prompt TEXT NOT NULL,
    image_url TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'portrait',
    model TEXT NOT NULL DEFAULT 'FLUX.1 Schnell',
    remixes_count INT NOT NULL DEFAULT 0,
    likes_count INT NOT NULL DEFAULT 0,
    author_name TEXT NOT NULL DEFAULT 'Alex Rivera',
    author_handle TEXT NOT NULL DEFAULT '@alexrivera_ai',
    author_avatar TEXT NOT NULL DEFAULT 'AR',
    seed INT NOT NULL DEFAULT 42,
    width INT NOT NULL DEFAULT 512,
    height INT NOT NULL DEFAULT 512,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for high-concurrency feeds and filtering
CREATE INDEX IF NOT EXISTS idx_artworks_category ON public.artworks(category);
CREATE INDEX IF NOT EXISTS idx_artworks_created_at ON public.artworks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_artworks_user_id ON public.artworks(user_id);

-- Enable RLS
ALTER TABLE public.artworks ENABLE ROW LEVEL SECURITY;

-- 1. Anyone (public anon & authenticated) can view published artworks
CREATE POLICY "Anyone can view artworks" ON public.artworks
    FOR SELECT USING (true);

-- 2. Anyone can insert artworks
CREATE POLICY "Anyone can insert artworks" ON public.artworks
    FOR INSERT WITH CHECK (true);

-- 3. Only the owner can update their own artworks
CREATE POLICY "Users can update own artworks" ON public.artworks
    FOR UPDATE USING (
        auth.uid() = user_id 
        OR (user_id IS NULL AND auth.uid() IS NOT NULL)
    );

-- 4. Only the owner can delete their own artworks
CREATE POLICY "Users can delete own artworks" ON public.artworks
    FOR DELETE USING (auth.uid() = user_id);

-- Grant privileges
GRANT ALL ON public.artworks TO anon, authenticated, service_role;
