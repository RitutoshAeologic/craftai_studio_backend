-- ====================================================================
-- CRAFTAI STUDIO — PRODUCTION DATABASE SCHEMA & REMOTE CONTROL SYSTEM
-- Aligned with rules.md, prod.md, and craftai_studio_platform_flow_and_architecture.md
-- ====================================================================

-- 0. Platform Settings & Remote Control Panel (Configurable anytime without app rebuilds)
CREATE TABLE IF NOT EXISTS public.app_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed initial settings: 500 Dev Credits + Royalty Disabled for Dev
INSERT INTO public.app_settings (key, value, description)
VALUES
    ('signup_credits', '500.00'::jsonb, 'Default credits awarded to new users on signup (Dev: 500, Prod: 5)'),
    ('royalty_config', '{"is_enabled": false, "royalty_percentage": 40.00, "min_payout_usd": 25.00}'::jsonb, 'Creator royalty feature flag and split config'),
    ('download_cost', '2.00'::jsonb, 'Flat 4K master export fee in credits (Rule 1)'),
    ('tier_prices', '{"flux": 2.00, "gemini": 3.00, "chatgpt": 3.00}'::jsonb, 'Uniform tier pricing brackets (Rule 3)')
ON CONFLICT (key) DO UPDATE 
SET value = EXCLUDED.value, updated_at = NOW();

ALTER TABLE public.app_settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read app settings" ON public.app_settings FOR SELECT USING (true);

-- 1. Wallets Table (Dual-Balance Ledger)
CREATE TABLE IF NOT EXISTS public.wallets (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    purchased_balance NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (purchased_balance >= 0),
    earned_royalty_balance NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (earned_royalty_balance >= 0),
    free_daily_balance NUMERIC(10, 2) NOT NULL DEFAULT 500.00 CHECK (free_daily_balance >= 0),
    total_generations INT NOT NULL DEFAULT 0,
    total_royalties_earned NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.wallets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own wallet" ON public.wallets FOR SELECT USING (auth.uid() = user_id);

-- 2. Consistent Characters Table (InstantID Face Lock)
CREATE TABLE IF NOT EXISTS public.characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    gender TEXT,
    reference_photo_urls TEXT[] NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.characters ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own characters" ON public.characters FOR ALL USING (auth.uid() = user_id);

-- 3. Explore Prompts Marketplace Table
CREATE TABLE IF NOT EXISTS public.explore_prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    author_handle TEXT NOT NULL DEFAULT '@creator',
    title TEXT NOT NULL,
    preview_url TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'Photorealism',
    masked_prompt_summary TEXT NOT NULL,
    prompt_cipher TEXT,
    cipher_iv TEXT,
    model_used TEXT NOT NULL DEFAULT 'flux',
    aspect_ratio TEXT NOT NULL DEFAULT '1:1',
    base_remix_fee NUMERIC(10, 2) NOT NULL DEFAULT 4.00,
    author_royalty_cut NUMERIC(10, 2) NOT NULL DEFAULT 1.60,
    total_remixes INT NOT NULL DEFAULT 0,
    likes_count INT NOT NULL DEFAULT 0,
    is_marketplace_public BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_explore_category_created ON public.explore_prompts (category, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_explore_likes ON public.explore_prompts (likes_count DESC);

ALTER TABLE public.explore_prompts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public prompts viewable by all" ON public.explore_prompts FOR SELECT USING (is_marketplace_public = TRUE);

-- 4. Jobs / Generations Table (Pay-to-Download + Remix Lineage)
CREATE TABLE IF NOT EXISTS public.jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    type TEXT NOT NULL DEFAULT 'IMAGE_GEN',
    status TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    prompt_text TEXT NOT NULL,
    model_used TEXT NOT NULL DEFAULT 'flux',
    aspect_ratio VARCHAR(10) NOT NULL DEFAULT '1:1',
    seed BIGINT DEFAULT 42,
    credits_deducted NUMERIC(10, 2) NOT NULL DEFAULT 2.00,
    preview_image_url TEXT,
    master_image_url TEXT,
    remixed_from_prompt_id UUID REFERENCES public.explore_prompts(id) ON DELETE SET NULL,
    is_download_unlocked BOOLEAN NOT NULL DEFAULT FALSE,
    download_unlocked_at TIMESTAMPTZ,
    download_cost NUMERIC(10, 2) NOT NULL DEFAULT 2.00,
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- High Performance Partial Indexes (< 5ms at 10M rows)
CREATE INDEX IF NOT EXISTS idx_jobs_user_created ON public.jobs (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_active_user ON public.jobs (user_id, created_at DESC) WHERE deleted_at IS NULL;

ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users view own jobs" ON public.jobs FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users update own jobs" ON public.jobs FOR UPDATE USING (auth.uid() = user_id);

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
CREATE POLICY "Users view relevant royalty logs" ON public.royalty_transactions FOR SELECT 
    USING (auth.uid() = buyer_user_id OR auth.uid() = creator_user_id);

-- 6. Database Trigger: Auto-Provision User Wallet with Configured Signup Credits (Default 500)
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
DECLARE
    initial_credits NUMERIC(10, 2) := 500.00;
    setting_row RECORD;
BEGIN
    -- Read from app_settings if available
    SELECT (value#>>'{}')::NUMERIC INTO initial_credits 
    FROM public.app_settings 
    WHERE key = 'signup_credits';

    IF initial_credits IS NULL THEN
        initial_credits := 500.00;
    END IF;

    -- Provision Wallet
    INSERT INTO public.wallets (user_id, free_daily_balance, purchased_balance)
    VALUES (NEW.id, initial_credits, 0.00)
    ON CONFLICT (user_id) DO NOTHING;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- 7. Storage Buckets (Public Read Access)
INSERT INTO storage.buckets (id, name, public)
VALUES 
    ('user_generations', 'user_generations', true),
    ('reference-images', 'reference-images', true)
ON CONFLICT (id) DO UPDATE SET public = true;
