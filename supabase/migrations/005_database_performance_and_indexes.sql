-- ====================================================================
-- CRAFTAI STUDIO — MIGRATION 005: PRODUCTION PERFORMANCE, INDEXES & RLS OPTIMIZATION
-- Industry Standard: O(1) Counter Cache, Subquery-Wrapped RLS, GIN Null-Safety
-- ====================================================================

-- 1. FIX GIN FULL-TEXT INDEX WITH COALESCE (Prevents NULL Index Collapse)
-- Standard Rule: String concatenation with NULL produces NULL in PostgreSQL.
-- Wrapping columns in COALESCE guarantees every row is indexed even if a field is empty.
DROP INDEX IF EXISTS public.idx_explore_prompts_fts;
CREATE INDEX idx_explore_prompts_fts ON public.explore_prompts 
USING gin (to_tsvector('english', 
    COALESCE(title, '') || ' ' || 
    COALESCE(masked_summary, '') || ' ' || 
    COALESCE(masked_prompt_summary, '') || ' ' || 
    COALESCE(category, '') || ' ' ||
    COALESCE(model_used, '')
));

-- 2. INDEX UNINDEXED FOREIGN KEYS (Eliminates Sequential Table Scans on Cascades & Joins)
CREATE INDEX IF NOT EXISTS idx_jobs_remixed_from 
    ON public.jobs (remixed_from_prompt_id) 
    WHERE remixed_from_prompt_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_royalty_prompt_id 
    ON public.royalty_transactions (prompt_id);

CREATE INDEX IF NOT EXISTS idx_royalty_creator_id 
    ON public.royalty_transactions (creator_user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_collection_items_explore 
    ON public.collection_items (explore_prompt_id) 
    WHERE explore_prompt_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_collection_items_job 
    ON public.collection_items (job_id) 
    WHERE job_id IS NOT NULL;

-- 3. COUNTER CACHE TRIGGER FOR COLLECTIONS (O(1) Instant Folder Size Without Joins)
ALTER TABLE public.collections 
    ADD COLUMN IF NOT EXISTS item_count INT NOT NULL DEFAULT 0;

CREATE OR REPLACE FUNCTION public.sync_collection_item_count()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        UPDATE public.collections 
        SET item_count = item_count + 1, updated_at = NOW()
        WHERE id = NEW.collection_id;
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        UPDATE public.collections 
        SET item_count = GREATEST(0, item_count - 1), updated_at = NOW()
        WHERE id = OLD.collection_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS trg_collection_item_counter ON public.collection_items;
CREATE TRIGGER trg_collection_item_counter
    AFTER INSERT OR DELETE ON public.collection_items
    FOR EACH ROW EXECUTE FUNCTION public.sync_collection_item_count();

-- 4. OPTIMIZE RLS POLICIES FOR 10X FASTER EVALUATION (Wrap auth.uid() in SELECT)
-- Wrapping auth.uid() in (SELECT auth.uid()) tells PostgreSQL planner to execute it as an
-- initPlan ONCE per query instead of once PER ROW, drastically improving large scan speeds.
DROP POLICY IF EXISTS "Users view own jobs" ON public.jobs;
CREATE POLICY "Users view own jobs" ON public.jobs 
    FOR SELECT USING ((SELECT auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users can view own wallet" ON public.wallets;
CREATE POLICY "Users can view own wallet" ON public.wallets 
    FOR SELECT USING ((SELECT auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users manage own collections" ON public.collections;
CREATE POLICY "Users manage own collections" ON public.collections 
    FOR ALL USING ((SELECT auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users manage own collection items" ON public.collection_items;
CREATE POLICY "Users manage own collection items" ON public.collection_items 
    FOR ALL USING ((SELECT auth.uid()) = user_id);

-- 5. AUTO-UPDATE UPDATED_AT TRIGGER
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_collections_updated_at ON public.collections;
CREATE TRIGGER trg_collections_updated_at
    BEFORE UPDATE ON public.collections
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

DROP TRIGGER IF EXISTS trg_wallets_updated_at ON public.wallets;
CREATE TRIGGER trg_wallets_updated_at
    BEFORE UPDATE ON public.wallets
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();
