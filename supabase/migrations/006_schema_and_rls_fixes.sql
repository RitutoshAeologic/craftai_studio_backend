-- ====================================================================
-- CRAFTAI STUDIO — MIGRATION 006: CRITICAL SCHEMA & RLS FIXES
-- Aligns Mobile App, Web Frontend & Backend Database Contracts
-- ====================================================================

-- 1. JOBS TABLE: Add job_id alias column and unique constraint
ALTER TABLE public.jobs 
    ADD COLUMN IF NOT EXISTS job_id TEXT;

-- Backfill job_id with id string if null
UPDATE public.jobs 
SET job_id = id::text 
WHERE job_id IS NULL;

-- Create unique index on job_id for clean upserts
CREATE UNIQUE INDEX IF NOT EXISTS uq_jobs_job_id ON public.jobs (job_id) WHERE job_id IS NOT NULL;

-- Also support prompt & preview_url column aliases for full backwards compatibility
ALTER TABLE public.jobs 
    ADD COLUMN IF NOT EXISTS prompt TEXT,
    ADD COLUMN IF NOT EXISTS preview_url TEXT;

UPDATE public.jobs SET prompt = prompt_text WHERE prompt IS NULL AND prompt_text IS NOT NULL;
UPDATE public.jobs SET preview_url = preview_image_url WHERE preview_url IS NULL AND preview_image_url IS NOT NULL;

-- 2. JOBS TABLE: Add INSERT policy for authenticated users
DROP POLICY IF EXISTS "Users insert own jobs" ON public.jobs;
CREATE POLICY "Users insert own jobs" ON public.jobs 
    FOR INSERT WITH CHECK ((SELECT auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users view own jobs" ON public.jobs;
CREATE POLICY "Users view own jobs" ON public.jobs 
    FOR SELECT USING ((SELECT auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users update own jobs" ON public.jobs;
CREATE POLICY "Users update own jobs" ON public.jobs 
    FOR UPDATE USING ((SELECT auth.uid()) = user_id);

-- 3. EXPLORE PROMPTS: Add INSERT & UPDATE policies for creators
DROP POLICY IF EXISTS "Users publish own prompts" ON public.explore_prompts;
CREATE POLICY "Users publish own prompts" ON public.explore_prompts 
    FOR INSERT WITH CHECK ((SELECT auth.uid()) = author_id);

DROP POLICY IF EXISTS "Users update own prompts" ON public.explore_prompts;
CREATE POLICY "Users update own prompts" ON public.explore_prompts 
    FOR UPDATE USING ((SELECT auth.uid()) = author_id);

DROP POLICY IF EXISTS "Public prompts viewable by all" ON public.explore_prompts;
CREATE POLICY "Public prompts viewable by all" ON public.explore_prompts 
    FOR SELECT USING (is_marketplace_public = TRUE OR (SELECT auth.uid()) = author_id);

-- 4. ATOMIC DATABASE RPC: deduct_user_credits
-- Safely deducts credits with row locking (Prevents double-spend race conditions)
CREATE OR REPLACE FUNCTION public.deduct_user_credits(
    p_user_id UUID,
    p_amount NUMERIC(10, 2),
    p_task_id TEXT DEFAULT NULL,
    p_reason TEXT DEFAULT 'generation'
)
RETURNS JSONB AS $$
DECLARE
    v_wallet RECORD;
    v_free_deduct NUMERIC(10, 2) := 0.00;
    v_purchased_deduct NUMERIC(10, 2) := 0.00;
    v_remaining_needed NUMERIC(10, 2) := p_amount;
    v_total_balance NUMERIC(10, 2);
    v_new_total NUMERIC(10, 2);
BEGIN
    -- 1. Fetch and row-lock the user wallet
    SELECT * INTO v_wallet 
    FROM public.wallets 
    WHERE user_id = p_user_id 
    FOR UPDATE;

    IF NOT FOUND THEN
        -- Auto-provision wallet if missing (500 free credits default)
        INSERT INTO public.wallets (user_id, free_daily_balance, purchased_balance)
        VALUES (p_user_id, 500.00, 0.00)
        RETURNING * INTO v_wallet;
    END IF;

    v_total_balance := COALESCE(v_wallet.free_daily_balance, 0.00) + COALESCE(v_wallet.purchased_balance, 0.00);

    -- 2. Check if sufficient balance
    IF v_total_balance < p_amount THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'error', 'Insufficient credit balance',
            'current_balance', v_total_balance,
            'required', p_amount
        );
    END IF;

    -- 3. Deduct first from free_daily_balance, then purchased_balance
    IF v_wallet.free_daily_balance >= v_remaining_needed THEN
        v_free_deduct := v_remaining_needed;
        v_remaining_needed := 0.00;
    ELSE
        v_free_deduct := v_wallet.free_daily_balance;
        v_remaining_needed := v_remaining_needed - v_wallet.free_daily_balance;
        v_purchased_deduct := v_remaining_needed;
    END IF;

    -- 4. Update wallet
    UPDATE public.wallets 
    SET 
        free_daily_balance = free_daily_balance - v_free_deduct,
        purchased_balance = purchased_balance - v_purchased_deduct,
        total_generations = total_generations + 1,
        updated_at = NOW()
    WHERE user_id = p_user_id;

    v_new_total := v_total_balance - p_amount;

    RETURN jsonb_build_object(
        'success', TRUE,
        'deducted', p_amount,
        'remaining_balance', v_new_total,
        'free_daily_balance', v_wallet.free_daily_balance - v_free_deduct,
        'purchased_balance', v_wallet.purchased_balance - v_purchased_deduct,
        'task_id', p_task_id
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 5. ATOMIC DATABASE RPC: refund_user_credits
-- Safely restores credits if a generation fails on backend
CREATE OR REPLACE FUNCTION public.refund_user_credits(
    p_user_id UUID,
    p_amount NUMERIC(10, 2),
    p_task_id TEXT DEFAULT NULL,
    p_reason TEXT DEFAULT 'generation_failed'
)
RETURNS JSONB AS $$
DECLARE
    v_wallet RECORD;
    v_new_balance NUMERIC(10, 2);
BEGIN
    SELECT * INTO v_wallet 
    FROM public.wallets 
    WHERE user_id = p_user_id 
    FOR UPDATE;

    IF NOT FOUND THEN
        INSERT INTO public.wallets (user_id, free_daily_balance, purchased_balance)
        VALUES (p_user_id, p_amount, 0.00)
        RETURNING * INTO v_wallet;
    ELSE
        UPDATE public.wallets 
        SET 
            free_daily_balance = free_daily_balance + p_amount,
            updated_at = NOW()
        WHERE user_id = p_user_id;
    END IF;

    SELECT (COALESCE(free_daily_balance, 0.00) + COALESCE(purchased_balance, 0.00)) INTO v_new_balance
    FROM public.wallets 
    WHERE user_id = p_user_id;

    RETURN jsonb_build_object(
        'success', TRUE,
        'refunded', p_amount,
        'new_balance', v_new_balance,
        'task_id', p_task_id
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
