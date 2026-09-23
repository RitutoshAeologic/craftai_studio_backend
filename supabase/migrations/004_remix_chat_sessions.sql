-- ====================================================================
-- CRAFTAI STUDIO — 004_REMIX_CHAT_SESSIONS_SCHEMA.SQL
-- Low-Latency, Relational Remix Chat & Prompt Tuning Architecture
-- Aligned with rules.md, prod.md Flow D, and Supabase RLS
-- ====================================================================

-- 1. Remix Sessions Table (Parent State for Conversational Remixing)
CREATE TABLE IF NOT EXISTS public.remix_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    anchor_image_url TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'explore' CHECK (source_type IN ('explore', 'library', 'custom')),
    remixed_from_prompt_id UUID REFERENCES public.explore_prompts(id) ON DELETE SET NULL,
    current_prompt TEXT NOT NULL,
    style_weight NUMERIC(3, 2) NOT NULL DEFAULT 0.60 CHECK (style_weight >= 0.10 AND style_weight <= 1.00),
    turn_count INT NOT NULL DEFAULT 0 CHECK (turn_count >= 0 AND turn_count <= 25),
    last_generated_job_id UUID REFERENCES public.jobs(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Fast Indexing for User Session Queries (< 2ms)
CREATE INDEX IF NOT EXISTS idx_remix_sessions_user_updated ON public.remix_sessions (user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_remix_sessions_prompt_id ON public.remix_sessions (remixed_from_prompt_id);

-- Enable RLS for Security
ALTER TABLE public.remix_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own remix sessions" ON public.remix_sessions
    FOR ALL USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- 2. Remix Messages Table (Turn Log, Diff Tags & Image Variations)
CREATE TABLE IF NOT EXISTS public.remix_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES public.remix_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    diff_added TEXT[] NOT NULL DEFAULT '{}'::TEXT[],
    diff_removed TEXT[] NOT NULL DEFAULT '{}'::TEXT[],
    suggested_chips TEXT[] NOT NULL DEFAULT '{}'::TEXT[],
    generated_image_url TEXT,
    model_used TEXT NOT NULL DEFAULT 'groq/qwen3.8-27b',
    latency_ms INT DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- High-Performance Composite Index for Message Stream Pagination
CREATE INDEX IF NOT EXISTS idx_remix_messages_session_time ON public.remix_messages (session_id, created_at ASC);

-- Enable RLS for Messages (Inherits ownership check via session)
ALTER TABLE public.remix_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own session messages" ON public.remix_messages
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.remix_sessions s 
            WHERE s.id = session_id AND s.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert own session messages" ON public.remix_messages
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.remix_sessions s 
            WHERE s.id = session_id AND s.user_id = auth.uid()
        )
    );

-- 3. Auto-update timestamp trigger on remix_sessions
CREATE OR REPLACE FUNCTION public.handle_remix_session_updated()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER on_remix_session_updated
    BEFORE UPDATE ON public.remix_sessions
    FOR EACH ROW EXECUTE FUNCTION public.handle_remix_session_updated();
