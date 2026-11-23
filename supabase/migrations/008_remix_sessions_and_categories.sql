-- ====================================================================
-- Migration 008: Remix Sessions, Master Categories, Credit Packages,
-- Two-Way Sync Triggers, and Creator Royalty Ledger
-- ====================================================================

-- 1. Master Categories Table & Foreign Keys
CREATE TABLE IF NOT EXISTS public.categories (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    slug VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon_name VARCHAR(50) NOT NULL DEFAULT 'auto_awesome',
    keywords TEXT[] NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.categories ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public can view active categories" ON public.categories;
CREATE POLICY "Public can view active categories" ON public.categories
    FOR SELECT USING (is_active = true);
GRANT SELECT ON public.categories TO anon, authenticated;
GRANT ALL ON public.categories TO service_role;

-- Populate Standard Starter Categories
INSERT INTO public.categories (slug, name, icon_name, keywords, sort_order) VALUES
('photorealism', 'Photorealism', 'camera_alt', ARRAY['photo', 'photograph', '85mm', 'portrait', 'realistic', 'dslr', 'raw photo', 'kodak', 'hyperrealistic', 'film grain', 'cinematic photo'], 1),
('anime', 'Anime', 'palette', ARRAY['anime', 'manga', 'ghibli', 'makoto shinkai', 'cel shaded', 'waifu', 'kawaii', 'chibi', 'otaku', 'japanese animation'], 2),
('cyberpunk', 'Cyberpunk', 'electric_bolt', ARRAY['cyberpunk', 'neon', 'futuristic', 'cyborg', 'synthwave', 'sci-fi', 'hologram', 'mecha', 'blade runner', 'matrix'], 3),
('3d-render', '3D Render', 'view_in_ar', ARRAY['3d', 'render', 'octane', 'blender', 'unreal engine', 'cgi', 'isometric', 'pixar', 'claymation', 'digital 3d'], 4),
('character', 'Character', 'person', ARRAY['character', 'portrait', 'warrior', 'knight', 'woman', 'man', 'hero', 'villain', 'avatar', 'ethereal noblewoman', 'samurai'], 5),
('architecture', 'Architecture', 'apartment', ARRAY['architecture', 'building', 'house', 'interior', 'facade', 'modern villa', 'skyscraper', 'room design', 'urban'], 6),
('product', 'Product', 'inventory_2', ARRAY['product', 'mockup', 'bottle', 'packaging', 'watch', 'sneakers', 'commercial', 'cosmetics', 'gadget', 'merchandise'], 7),
('general', 'General', 'auto_awesome', ARRAY['art', 'illustration', 'creative', 'concept', 'abstract'], 99)
ON CONFLICT (slug) DO UPDATE SET 
    name = EXCLUDED.name,
    icon_name = EXCLUDED.icon_name,
    keywords = EXCLUDED.keywords,
    sort_order = EXCLUDED.sort_order;

-- Link category_id in jobs and explore_prompts
ALTER TABLE public.jobs 
    ADD COLUMN IF NOT EXISTS category VARCHAR(50) DEFAULT 'General',
    ADD COLUMN IF NOT EXISTS category_id TEXT REFERENCES public.categories(id) ON DELETE SET NULL;

ALTER TABLE public.explore_prompts 
    ADD COLUMN IF NOT EXISTS category_id TEXT REFERENCES public.categories(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_jobs_user_category ON public.jobs (user_id, category, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_explore_prompts_cat_lower ON public.explore_prompts (LOWER(category), created_at DESC);
CREATE INDEX IF NOT EXISTS idx_explore_prompts_category_id ON public.explore_prompts (category_id);

-- 2. Atomic Like Counter RPC
CREATE OR REPLACE FUNCTION public.toggle_prompt_like(prompt_id UUID, is_liked BOOLEAN)
RETURNS INT AS $$
DECLARE
    new_count INT;
BEGIN
    UPDATE public.explore_prompts
    SET likes_count = GREATEST(0, COALESCE(likes_count, 0) + (CASE WHEN is_liked THEN 1 ELSE -1 END))
    WHERE id = prompt_id
    RETURNING likes_count INTO new_count;

    UPDATE public.artworks
    SET likes_count = GREATEST(0, COALESCE(likes_count, 0) + (CASE WHEN is_liked THEN 1 ELSE -1 END))
    WHERE id = prompt_id::text;

    RETURN COALESCE(new_count, 0);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
GRANT EXECUTE ON FUNCTION public.toggle_prompt_like TO anon, authenticated, service_role;

-- 3. Dynamic Credit Packages Table & Payment Audit Ledger
CREATE TABLE IF NOT EXISTS public.credit_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    badge TEXT,
    price_inr NUMERIC(10, 2) NOT NULL,
    price_usd NUMERIC(10, 2) NOT NULL DEFAULT 1.99,
    credits INT NOT NULL,
    bonus_credits INT NOT NULL DEFAULT 0,
    features JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_popular BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.credit_packages ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public can view active packages" ON public.credit_packages;
CREATE POLICY "Public can view active packages" ON public.credit_packages
    FOR SELECT USING (is_active = TRUE);
GRANT SELECT ON public.credit_packages TO anon, authenticated;
GRANT ALL ON public.credit_packages TO service_role;

INSERT INTO public.credit_packages (package_id, name, badge, price_inr, price_usd, credits, bonus_credits, is_popular, sort_order, features)
VALUES 
('pack_starter_99', 'Starter Pack', 'Quick Trial', 99.00, 1.29, 100, 0, FALSE, 1, '["50 High-Res Generations", "FLUX & SDXL Access", "InstantID Character Lock", "Community Publishing"]'::jsonb),
('pack_creator_249', 'Creator Pack', 'Most Popular', 249.00, 2.99, 250, 50, TRUE, 2, '["150 High-Res Generations", "50 Free Bonus Credits", "4K Lossless Downloads", "Commercial Usage Rights", "Fast Queue Priority"]'::jsonb),
('pack_pro_499', 'Pro Studio Pack', 'Best Value', 499.00, 5.99, 500, 150, FALSE, 3, '["325 High-Res Generations", "150 Free Bonus Credits", "Unlimited 4K Upscaling", "All AI Editing Tools Included", "Instant Support"]'::jsonb),
('pack_master_999', 'Master Agency Pack', 'Max Power', 999.00, 11.99, 1000, 500, FALSE, 4, '["750 High-Res Generations", "500 Mega Bonus Credits", "Full Commercial License", "Zero Watermark", "VIP Generation Server"]'::jsonb)
ON CONFLICT (package_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS public.payment_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    package_id TEXT NOT NULL REFERENCES public.credit_packages(package_id),
    razorpay_order_id TEXT NOT NULL,
    razorpay_payment_id TEXT UNIQUE,
    razorpay_signature TEXT,
    amount_inr NUMERIC(10, 2) NOT NULL,
    credits_credited INT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    status TEXT NOT NULL DEFAULT 'created',
    payment_method TEXT,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payment_transactions_user_id ON public.payment_transactions (user_id);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_package_id ON public.payment_transactions (package_id);

ALTER TABLE public.payment_transactions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users view own transactions" ON public.payment_transactions;
CREATE POLICY "Users view own transactions" ON public.payment_transactions
    FOR SELECT USING ((SELECT auth.uid()) = user_id);
GRANT ALL ON public.payment_transactions TO authenticated, service_role;

CREATE TABLE IF NOT EXISTS public.wallet_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    amount NUMERIC(10, 2) NOT NULL,
    balance_after NUMERIC(10, 2) NOT NULL,
    event_type TEXT NOT NULL,
    description TEXT NOT NULL,
    reference_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wallet_ledger_user ON public.wallet_ledger(user_id, created_at DESC);
ALTER TABLE public.wallet_ledger ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users view own ledger" ON public.wallet_ledger;
CREATE POLICY "Users view own ledger" ON public.wallet_ledger
    FOR SELECT USING ((SELECT auth.uid()) = user_id);
GRANT ALL ON public.wallet_ledger TO authenticated, service_role;

-- 4. Persistent Remix Sessions Table
CREATE TABLE IF NOT EXISTS public.remix_sessions (
    id TEXT PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    anchor_image_url TEXT NOT NULL,
    source_type VARCHAR(50) NOT NULL DEFAULT 'explore',
    remixed_from_prompt_id UUID REFERENCES public.explore_prompts(id) ON DELETE SET NULL,
    current_prompt TEXT NOT NULL,
    style_weight NUMERIC(3, 2) NOT NULL DEFAULT 0.60,
    turn_count INT NOT NULL DEFAULT 0,
    last_generated_job_id TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    messages JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_remix_sessions_user ON public.remix_sessions(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_remix_sessions_prompt ON public.remix_sessions(remixed_from_prompt_id);

ALTER TABLE public.remix_sessions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users manage own remix sessions" ON public.remix_sessions;
CREATE POLICY "Users manage own remix sessions" ON public.remix_sessions
    FOR ALL USING ((SELECT auth.uid()) = user_id OR user_id IS NULL);
GRANT ALL ON public.remix_sessions TO anon, authenticated, service_role;

-- 5. Creator Royalty RPCs
CREATE OR REPLACE FUNCTION public.increment_creator_royalty(
    p_creator_id UUID,
    p_amount NUMERIC(10, 2),
    p_prompt_id UUID DEFAULT NULL,
    p_buyer_id UUID DEFAULT NULL
)
RETURNS JSONB AS $$
DECLARE
    v_wallet public.wallets;
    v_new_balance NUMERIC(10, 2);
    v_prompt_title TEXT;
BEGIN
    IF p_prompt_id IS NOT NULL THEN
        SELECT title INTO v_prompt_title FROM public.explore_prompts WHERE id = p_prompt_id;
    END IF;
    v_prompt_title := COALESCE(v_prompt_title, 'Community Artwork');

    SELECT * INTO v_wallet FROM public.wallets WHERE user_id = p_creator_id FOR UPDATE;
    IF NOT FOUND THEN
        INSERT INTO public.wallets (user_id, free_daily_balance, purchased_balance, earned_royalty_balance, total_royalties_earned, credits)
        VALUES (p_creator_id, 500.00, 0.00, p_amount, p_amount, 500.00 + p_amount)
        RETURNING * INTO v_wallet;
    ELSE
        UPDATE public.wallets 
        SET 
            earned_royalty_balance = COALESCE(earned_royalty_balance, 0.00) + p_amount,
            total_royalties_earned = COALESCE(total_royalties_earned, 0.00) + p_amount,
            credits = credits + p_amount,
            updated_at = NOW()
        WHERE user_id = p_creator_id
        RETURNING * INTO v_wallet;
    END IF;

    v_new_balance := v_wallet.credits;

    INSERT INTO public.wallet_ledger (
        user_id, amount, balance_after, event_type, description, reference_id
    ) VALUES (
        p_creator_id,
        p_amount,
        v_new_balance,
        'royalty',
        'Creator Royalty: Community remix of "' || v_prompt_title || '" (+' || p_amount || ' Credits)',
        COALESCE(p_prompt_id::text, 'remix')
    );

    RETURN jsonb_build_object(
        'success', TRUE,
        'credited', p_amount,
        'new_balance', v_new_balance,
        'creator_id', p_creator_id
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
GRANT EXECUTE ON FUNCTION public.increment_creator_royalty TO authenticated, service_role;

CREATE OR REPLACE FUNCTION public.increment_prompt_remix_count(p_prompt_id UUID)
RETURNS INT AS $$
DECLARE
    new_count INT;
BEGIN
    UPDATE public.explore_prompts
    SET 
        remixes_count = COALESCE(remixes_count, 0) + 1,
        total_remixes = COALESCE(total_remixes, 0) + 1
    WHERE id = p_prompt_id
    RETURNING remixes_count INTO new_count;

    UPDATE public.artworks
    SET 
        remixes_count = COALESCE(remixes_count, 0) + 1,
        total_remixes = COALESCE(total_remixes, 0) + 1
    WHERE id = p_prompt_id::text;

    RETURN COALESCE(new_count, 1);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
GRANT EXECUTE ON FUNCTION public.increment_prompt_remix_count TO anon, authenticated, service_role;

