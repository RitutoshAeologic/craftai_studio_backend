-- ====================================================================
-- CRAFTAI STUDIO — PRODUCTION DATABASE SCHEMA & RLS POLICIES (SUPABASE)
-- ====================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Wallets Table (Dual-Balance Ledger)
CREATE TABLE IF NOT EXISTS public.wallets (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    purchased_balance NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (purchased_balance >= 0),
    earned_royalty_balance NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (earned_royalty_balance >= 0),
    free_daily_balance NUMERIC(10, 2) NOT NULL DEFAULT 5.00 CHECK (free_daily_balance >= 0),
    total_generations INT NOT NULL DEFAULT 0,
    total_royalties_earned NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.wallets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own wallet" ON public.wallets
    FOR SELECT USING (auth.uid() = user_id);

-- 2. Consistent Characters Table (InstantID Face Lock)
CREATE TABLE IF NOT EXISTS public.characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    gender TEXT,
    reference_photo_urls TEXT[] NOT NULL,
    face_embedding vector(512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.characters ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own characters" ON public.characters
    FOR ALL USING (auth.uid() = user_id);

-- 3. Explore Prompts Marketplace Table (pgvector Semantic Search)
CREATE TABLE IF NOT EXISTS public.explore_prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    preview_url TEXT NOT NULL,
    master_url TEXT NOT NULL,
    category TEXT NOT NULL,
    masked_prompt_summary TEXT NOT NULL,
    prompt_cipher TEXT NOT NULL,
    cipher_iv TEXT NOT NULL,
    prompt_template TEXT NOT NULL,
    template_variables JSONB NOT NULL DEFAULT '[]'::jsonb,
    model_used TEXT NOT NULL DEFAULT 'flux_schnell',
    aspect_ratio TEXT NOT NULL DEFAULT '9:16',
    base_remix_fee NUMERIC(10, 2) NOT NULL DEFAULT 4.00,
    author_royalty_cut NUMERIC(10, 2) NOT NULL DEFAULT 1.60,
    total_remixes INT NOT NULL DEFAULT 0,
    likes_count INT NOT NULL DEFAULT 0,
    prompt_embedding vector(768),
    is_marketplace_public BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_explore_prompts_vector ON public.explore_prompts
USING ivfflat (prompt_embedding vector_cosine_ops) WITH (lists = 100);

ALTER TABLE public.explore_prompts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public prompts viewable by all" ON public.explore_prompts
    FOR SELECT USING (is_marketplace_public = TRUE);

-- 4. Jobs Table (Generation & Pay-to-Download Licensing)
CREATE TABLE IF NOT EXISTS public.jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    type TEXT NOT NULL DEFAULT 'IMAGE_GEN',
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    model_used TEXT NOT NULL,
    tokens_analyzed INT NOT NULL DEFAULT 0,
    credits_deducted NUMERIC(10, 2) NOT NULL,
    preview_image_url TEXT,
    master_image_url TEXT,
    is_download_unlocked BOOLEAN NOT NULL DEFAULT FALSE,
    download_unlocked_at TIMESTAMPTZ,
    download_cost NUMERIC(10, 2) NOT NULL DEFAULT 2.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users view own jobs" ON public.jobs
    FOR SELECT USING (auth.uid() = user_id);

-- 5. Royalty Transactions Table (Financial Audit Trail)
CREATE TABLE IF NOT EXISTS public.royalty_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    buyer_user_id UUID NOT NULL REFERENCES auth.users(id),
    creator_user_id UUID NOT NULL REFERENCES auth.users(id),
    prompt_id UUID NOT NULL REFERENCES public.explore_prompts(id),
    total_fee_charged NUMERIC(10, 2) NOT NULL,
    creator_royalty_credited NUMERIC(10, 2) NOT NULL,
    platform_fee_retained NUMERIC(10, 2) NOT NULL,
    funded_from TEXT NOT NULL DEFAULT 'purchased_balance',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.royalty_transactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users view relevant royalty logs" ON public.royalty_transactions
    FOR SELECT USING (auth.uid() = buyer_user_id OR auth.uid() = creator_user_id);
