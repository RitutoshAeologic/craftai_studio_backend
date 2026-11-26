-- ==============================================================================
-- Migration 010: Multi-Provider AI Gateway, Dynamic Supabase Secrets,
--                Usage Telemetry & 2-Phase Atomic Credit Reservation
-- ==============================================================================
-- Design:
--   1. Keeps all live tables intact (wallets, wallet_ledger, jobs, explore_prompts, artworks).
--   2. Stores paid API keys in `ai_provider_secrets` (strictly service_role ONLY).
--   3. When a paid key is missing, backend automatically routes to `fallback_model_key` (local/free).
--   4. The moment an admin inserts a key in Supabase Dashboard, ConfigService hot-reloads
--      within 60s and unlocks the paid AI model with ZERO redeploy.
-- ==============================================================================

-- 1. AI Providers Catalog (Public metadata, NO secrets)
CREATE TABLE IF NOT EXISTS public.ai_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_key TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    base_url TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    priority INT NOT NULL DEFAULT 100,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.ai_providers ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public can read active ai_providers" ON public.ai_providers;
CREATE POLICY "Public can read active ai_providers"
    ON public.ai_providers FOR SELECT USING (is_active = TRUE);
GRANT SELECT ON public.ai_providers TO anon, authenticated;
GRANT ALL ON public.ai_providers TO service_role;

-- 2. AI Provider Secrets (STRICTLY service_role ONLY — ZERO anon/authenticated access)
CREATE TABLE IF NOT EXISTS public.ai_provider_secrets (
    provider_key TEXT PRIMARY KEY REFERENCES public.ai_providers(provider_key) ON DELETE CASCADE,
    api_key TEXT NOT NULL DEFAULT '',
    extra_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.ai_provider_secrets ENABLE ROW LEVEL SECURITY;
-- Intentionally NO SELECT/INSERT/UPDATE/DELETE policies for anon or authenticated!
-- Only service_role (backend admin client) can read/manage secrets.
REVOKE ALL ON public.ai_provider_secrets FROM anon, authenticated;
GRANT ALL ON public.ai_provider_secrets TO service_role;

-- 3. Config-Driven AI Models Catalog
CREATE TABLE IF NOT EXISTS public.ai_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_key TEXT UNIQUE NOT NULL,
    provider_key TEXT NOT NULL REFERENCES public.ai_providers(provider_key) ON DELETE CASCADE,
    external_model_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    tasks TEXT[] NOT NULL DEFAULT ARRAY['text_to_image'],
    tier TEXT NOT NULL DEFAULT 'standard' CHECK (tier IN ('economy', 'standard', 'premium', 'editing')),
    credit_cost NUMERIC(10, 2) NOT NULL DEFAULT 2.00,
    fallback_model_key TEXT DEFAULT 'local_sdxl',
    capabilities JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.ai_models ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public can read active ai_models" ON public.ai_models;
CREATE POLICY "Public can read active ai_models"
    ON public.ai_models FOR SELECT USING (is_active = TRUE);
GRANT SELECT ON public.ai_models TO anon, authenticated;
GRANT ALL ON public.ai_models TO service_role;

-- 4. AI Usage & Cost Telemetry Logs
CREATE TABLE IF NOT EXISTS public.ai_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,  -- Nullable & no strict FK so dev/guest UUID (00000000-...) never fails with 23503
    job_id UUID,
    task_id TEXT,
    provider_key TEXT NOT NULL,
    model_key TEXT NOT NULL,
    operation TEXT NOT NULL DEFAULT 'text_to_image',
    input_tokens INT NOT NULL DEFAULT 0,
    output_tokens INT NOT NULL DEFAULT 0,
    image_count INT NOT NULL DEFAULT 1,
    resolution TEXT DEFAULT '1024x1024',
    provider_cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0.000000,
    credits_charged NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    latency_ms INT NOT NULL DEFAULT 0,
    is_fallback_used BOOLEAN NOT NULL DEFAULT FALSE,
    status TEXT NOT NULL DEFAULT 'completed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_user_created ON public.ai_usage_logs (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_provider_model ON public.ai_usage_logs (provider_key, model_key, created_at DESC);

ALTER TABLE public.ai_usage_logs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view own usage logs" ON public.ai_usage_logs;
CREATE POLICY "Users can view own usage logs"
    ON public.ai_usage_logs FOR SELECT USING (auth.uid() = user_id);
GRANT SELECT ON public.ai_usage_logs TO authenticated;
GRANT ALL ON public.ai_usage_logs TO service_role;

-- 5. Extend Existing `public.jobs` Table for Idempotency, Gateway Tracking & Reservations
ALTER TABLE public.jobs
    ADD COLUMN IF NOT EXISTS idempotency_key TEXT,
    ADD COLUMN IF NOT EXISTS provider_key TEXT,
    ADD COLUMN IF NOT EXISTS model_key TEXT,
    ADD COLUMN IF NOT EXISTS provider_job_id TEXT,
    ADD COLUMN IF NOT EXISTS estimated_cost NUMERIC(10, 2),
    ADD COLUMN IF NOT EXISTS actual_cost NUMERIC(10, 2),
    ADD COLUMN IF NOT EXISTS reserved_until TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS credit_status TEXT DEFAULT 'settled',
    ADD COLUMN IF NOT EXISTS parent_job_id UUID,
    ADD COLUMN IF NOT EXISTS version INT DEFAULT 1;

CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_user_idempotency
    ON public.jobs (user_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_jobs_stale_reserved
    ON public.jobs (status, reserved_until)
    WHERE credit_status = 'reserved';

-- 6. Seed Providers (Local/Free active immediately + Paid Providers ready for key injection)
INSERT INTO public.ai_providers (provider_key, display_name, base_url, is_active, priority)
VALUES
    ('local', 'Local Inference / Tools', 'http://127.0.0.1:8001', TRUE, 10),
    ('cloudflare', 'Cloudflare Workers AI', 'https://api.cloudflare.com/client/v4', TRUE, 20),
    ('huggingface', 'Hugging Face Inference', 'https://router.huggingface.co', TRUE, 30),
    ('fal', 'fal.ai Cloud Diffusion', 'https://queue.fal.run', TRUE, 40),
    ('openai', 'OpenAI Images & Vision', 'https://api.openai.com/v1', TRUE, 50),
    ('google', 'Google Gemini Multimodal', 'https://generativelanguage.googleapis.com', TRUE, 60),
    ('openrouter', 'OpenRouter Text Gateway', 'https://openrouter.ai/api/v1', TRUE, 70)
ON CONFLICT (provider_key) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    base_url = EXCLUDED.base_url,
    updated_at = NOW();

-- 7. Seed Curated Models Catalog (Live verified slugs + Local fallback mapping)
INSERT INTO public.ai_models (
    model_key, provider_key, external_model_id, display_name,
    tasks, tier, credit_cost, fallback_model_key, capabilities, is_active, sort_order
)
VALUES
(
    'local_sdxl', 'local', 'sdxl-lightning-local', 'CraftAI Local Fast Engine',
    ARRAY['text_to_image', 'image_edit'], 'economy', 2.00, NULL,
    '{"supports_facelock": false, "supports_negative_prompt": true, "supports_transparency": false, "is_local": true}'::jsonb,
    TRUE, 1
),
(
    'cloudflare_flux', 'cloudflare', '@cf/black-forest-labs/flux-1-schnell', 'FLUX.1 Schnell (Serverless)',
    ARRAY['text_to_image'], 'economy', 2.00, 'local_sdxl',
    '{"supports_facelock": false, "supports_negative_prompt": false, "supports_transparency": false, "is_local": false}'::jsonb,
    TRUE, 2
),
(
    'flux_schnell', 'fal', 'fal-ai/flux/schnell', 'FLUX.1 Schnell (fal.ai)',
    ARRAY['text_to_image'], 'economy', 2.00, 'cloudflare_flux',
    '{"supports_facelock": false, "supports_negative_prompt": false, "supports_transparency": false, "aspect_ratio_map": {"1:1": "square_hd", "16:9": "landscape_16_9", "9:16": "portrait_16_9", "4:5": "portrait_4_3"}}'::jsonb,
    TRUE, 3
),
(
    'flux_pulid_facelock', 'fal', 'fal-ai/flux-pulid', 'FLUX PuLID (Face-Lock Remix)',
    ARRAY['face_lock_remix', 'text_to_image'], 'standard', 3.00, 'local_sdxl',
    '{"supports_facelock": true, "supports_negative_prompt": true, "supports_transparency": false}'::jsonb,
    TRUE, 4
),
(
    'gemini_flash_image', 'google', 'gemini-2.5-flash-image', 'Gemini 2.5 Flash Image (Edit)',
    ARRAY['text_to_image', 'image_edit'], 'editing', 3.00, 'local_sdxl',
    '{"supports_facelock": false, "supports_negative_prompt": false, "supports_transparency": false}'::jsonb,
    TRUE, 5
),
(
    'gpt_image_1', 'openai', 'gpt-image-1', 'GPT Image 1 (HD Studio)',
    ARRAY['text_to_image', 'image_edit'], 'premium', 4.00, 'cloudflare_flux',
    '{"supports_facelock": false, "supports_negative_prompt": false, "supports_transparency": true, "aspect_ratio_map": {"1:1": "1024x1024", "16:9": "1536x1024", "9:16": "1024x1536"}}'::jsonb,
    TRUE, 6
)
ON CONFLICT (model_key) DO UPDATE SET
    provider_key = EXCLUDED.provider_key,
    external_model_id = EXCLUDED.external_model_id,
    display_name = EXCLUDED.display_name,
    tasks = EXCLUDED.tasks,
    tier = EXCLUDED.tier,
    credit_cost = EXCLUDED.credit_cost,
    fallback_model_key = EXCLUDED.fallback_model_key,
    capabilities = EXCLUDED.capabilities,
    sort_order = EXCLUDED.sort_order,
    updated_at = NOW();

-- 8. Two-Phase Credit Reservation & Settlement RPCs (Row-Locked + Idempotent)
CREATE OR REPLACE FUNCTION public.reserve_user_credits(
    p_user_id UUID,
    p_amount NUMERIC,
    p_task_id TEXT DEFAULT NULL,
    p_idempotency_key TEXT DEFAULT NULL,
    p_ttl_seconds INT DEFAULT 300
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_free NUMERIC;
    v_purch NUMERIC;
    v_total NUMERIC;
    v_deduct_free NUMERIC;
    v_deduct_purch NUMERIC;
    v_existing_job RECORD;
BEGIN
    -- Bypass credit checks for dev/guest sessions
    IF p_user_id IS NULL OR p_user_id = '00000000-0000-0000-0000-000000000000'::uuid THEN
        RETURN jsonb_build_object('success', TRUE, 'reserved', 0, 'is_dev', TRUE, 'remaining_balance', 500.0);
    END IF;

    IF p_amount <= 0 THEN
        RETURN jsonb_build_object('success', TRUE, 'reserved', 0, 'idempotent_hit', FALSE);
    END IF;

    -- Idempotency check: if already reserved for this key, do not double-charge
    IF p_idempotency_key IS NOT NULL THEN
        SELECT id, credit_status, estimated_cost INTO v_existing_job
        FROM public.jobs
        WHERE user_id = p_user_id AND idempotency_key = p_idempotency_key
        LIMIT 1;
        IF FOUND THEN
            RETURN jsonb_build_object(
                'success', TRUE,
                'idempotent_hit', TRUE,
                'reserved', COALESCE(v_existing_job.estimated_cost, p_amount),
                'job_id', v_existing_job.id
            );
        END IF;
    END IF;

    SELECT free_daily_balance, purchased_balance
    INTO v_free, v_purch
    FROM public.wallets
    WHERE user_id = p_user_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Wallet not found');
    END IF;

    v_total := COALESCE(v_free, 0) + COALESCE(v_purch, 0);
    IF v_total < p_amount THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Insufficient credits', 'current_balance', v_total);
    END IF;

    v_deduct_free := LEAST(COALESCE(v_free, 0), p_amount);
    v_deduct_purch := p_amount - v_deduct_free;

    UPDATE public.wallets
    SET
        free_daily_balance = free_daily_balance - v_deduct_free,
        purchased_balance = purchased_balance - v_deduct_purch,
        updated_at = NOW()
    WHERE user_id = p_user_id;

    RETURN jsonb_build_object(
        'success', TRUE,
        'idempotent_hit', FALSE,
        'reserved', p_amount,
        'remaining_balance', v_total - p_amount,
        'reserved_until', (NOW() + make_interval(secs => p_ttl_seconds))
    );
END;
$$;

CREATE OR REPLACE FUNCTION public.settle_or_refund_credits(
    p_user_id UUID,
    p_task_id TEXT,
    p_reserved_amount NUMERIC,
    p_actual_cost NUMERIC,
    p_status TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_refund NUMERIC := 0;
    v_updated_rows INT := 0;
BEGIN
    IF p_user_id IS NULL OR p_user_id = '00000000-0000-0000-0000-000000000000'::uuid THEN
        RETURN jsonb_build_object('success', TRUE, 'refunded', 0, 'is_dev', TRUE, 'status', p_status);
    END IF;

    -- Idempotent guard: only settle/refund if job is still in 'reserved' state (prevents double-refund race)
    UPDATE public.jobs
    SET
        credit_status = CASE WHEN p_status IN ('failed', 'cancelled', 'moderation_rejected') THEN 'refunded' ELSE 'settled' END,
        actual_cost = CASE WHEN p_status IN ('failed', 'cancelled', 'moderation_rejected') THEN 0 ELSE COALESCE(p_actual_cost, p_reserved_amount) END
    WHERE user_id = p_user_id
      AND job_id = p_task_id
      AND COALESCE(credit_status, 'reserved') = 'reserved';

    GET DIAGNOSTICS v_updated_rows = ROW_COUNT;
    IF v_updated_rows = 0 THEN
        RETURN jsonb_build_object('success', TRUE, 'refunded', 0, 'already_processed', TRUE);
    END IF;

    IF p_status IN ('failed', 'cancelled', 'moderation_rejected') THEN
        v_refund := GREATEST(0, COALESCE(p_reserved_amount, 0));
    ELSIF p_status = 'completed' AND p_actual_cost IS NOT NULL AND p_reserved_amount > p_actual_cost THEN
        v_refund := p_reserved_amount - p_actual_cost;
    END IF;

    IF v_refund > 0 THEN
        UPDATE public.wallets
        SET
            purchased_balance = purchased_balance + v_refund,
            updated_at = NOW()
        WHERE user_id = p_user_id;
    END IF;

    RETURN jsonb_build_object('success', TRUE, 'refunded', v_refund, 'status', p_status);
END;
$$;

-- 9. Stale Job Reaper (Auto-refunds jobs stuck in reserved state past TTL)
CREATE OR REPLACE FUNCTION public.reap_stale_reserved_jobs()
RETURNS INT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_job RECORD;
    v_count INT := 0;
BEGIN
    FOR v_job IN
        SELECT id, user_id, job_id, estimated_cost
        FROM public.jobs
        WHERE credit_status = 'reserved'
          AND status IN ('pending', 'processing')
          AND reserved_until IS NOT NULL
          AND reserved_until < NOW()
        FOR UPDATE SKIP LOCKED
    LOOP
        UPDATE public.wallets
        SET purchased_balance = purchased_balance + COALESCE(v_job.estimated_cost, 0),
            updated_at = NOW()
        WHERE user_id = v_job.user_id;

        UPDATE public.jobs
        SET status = 'failed',
            credit_status = 'refunded',
            actual_cost = 0
        WHERE id = v_job.id;

        v_count := v_count + 1;
    END LOOP;
    RETURN v_count;
END;
$$;

