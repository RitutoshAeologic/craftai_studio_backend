-- Create public artworks table for marketplace publishing
CREATE TABLE IF NOT EXISTS public.artworks (
    id TEXT PRIMARY KEY,
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

-- Enable RLS and grant public read and insert access
ALTER TABLE public.artworks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view artworks" ON public.artworks
    FOR SELECT USING (true);

CREATE POLICY "Anyone can insert artworks" ON public.artworks
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Anyone can update artworks" ON public.artworks
    FOR UPDATE USING (true);

-- Grant privileges
GRANT ALL ON public.artworks TO anon, authenticated, service_role;
