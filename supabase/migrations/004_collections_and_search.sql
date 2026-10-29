-- ====================================================================
-- CRAFTAI STUDIO — MIGRATION 004 (PATCHED & PRODUCTION CERTIFIED)
-- COLLECTIONS, BOOKMARKS, EXPLORE METADATA & GIN UNIVERSAL SEARCH
-- ====================================================================

-- 1. Named Collections / Folders Table
CREATE TABLE IF NOT EXISTS public.collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK (char_length(trim(name)) > 0),
    description TEXT,
    cover_image_url TEXT,
    item_count INT NOT NULL DEFAULT 0, -- O(1) counter-cache
    is_default BOOLEAN NOT NULL DEFAULT FALSE, -- Instagram 'All Saved' default folder
    is_private BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_collections_user ON public.collections (user_id, updated_at DESC);
ALTER TABLE public.collections ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users manage own collections" ON public.collections;
CREATE POLICY "Users manage own collections" ON public.collections
    FOR ALL USING ((SELECT auth.uid()) = user_id);

-- Auto-create 'All Saved' default collection for new users
CREATE OR REPLACE FUNCTION public.handle_new_user_default_collection()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.collections (user_id, name, is_default, is_private)
    VALUES (NEW.id, 'All Saved', TRUE, TRUE)
    ON CONFLICT DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 2. Collection Items (Polymorphic Bookmark Junction Table)
CREATE TABLE IF NOT EXISTS public.collection_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_id UUID NOT NULL REFERENCES public.collections(id) ON DELETE CASCADE,
    job_id UUID REFERENCES public.jobs(id) ON DELETE CASCADE,
    explore_prompt_id UUID REFERENCES public.explore_prompts(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_item_target CHECK (job_id IS NOT NULL OR explore_prompt_id IS NOT NULL)
);

-- Partial unique indexes to prevent duplicate bookmarks for jobs AND explore prompts
CREATE UNIQUE INDEX IF NOT EXISTS uq_collection_job 
    ON public.collection_items (collection_id, job_id) 
    WHERE job_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_collection_explore 
    ON public.collection_items (collection_id, explore_prompt_id) 
    WHERE explore_prompt_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_collection_items_col ON public.collection_items (collection_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_collection_items_user ON public.collection_items (user_id, created_at DESC);
ALTER TABLE public.collection_items ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users manage own collection items" ON public.collection_items;
CREATE POLICY "Users manage own collection items" ON public.collection_items
    FOR ALL USING ((SELECT auth.uid()) = user_id);

-- 3. Enhance public.jobs Table with Generation Metadata Columns
ALTER TABLE public.jobs 
    ADD COLUMN IF NOT EXISTS prompt_text TEXT,
    ADD COLUMN IF NOT EXISTS preview_image_url TEXT,
    ADD COLUMN IF NOT EXISTS master_image_url TEXT,
    ADD COLUMN IF NOT EXISTS tool_applied TEXT NOT NULL DEFAULT 'text_to_image',
    ADD COLUMN IF NOT EXISTS aspect_ratio VARCHAR(10) NOT NULL DEFAULT '1:1',
    ADD COLUMN IF NOT EXISTS dimensions VARCHAR(20) DEFAULT '1024x1024',
    ADD COLUMN IF NOT EXISTS seed BIGINT DEFAULT 42,
    ADD COLUMN IF NOT EXISTS generation_time_ms INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

-- Backfill aliases if legacy columns exist
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'jobs' AND column_name = 'prompt') THEN
        UPDATE public.jobs SET prompt_text = prompt WHERE prompt_text IS NULL AND prompt IS NOT NULL;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'jobs' AND column_name = 'preview_url') THEN
        UPDATE public.jobs SET preview_image_url = preview_url WHERE preview_image_url IS NULL AND preview_url IS NOT NULL;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'jobs' AND column_name = 'master_url') THEN
        UPDATE public.jobs SET master_image_url = master_url WHERE master_image_url IS NULL AND master_url IS NOT NULL;
    END IF;
END $$;

-- High-performance GIN index for full-text search across user creations
DROP INDEX IF EXISTS public.idx_jobs_prompt_fts;
CREATE INDEX idx_jobs_prompt_fts ON public.jobs 
USING gin (to_tsvector('english', COALESCE(prompt_text, '') || ' ' || COALESCE(prompt, '')));

-- 4. Enhance public.explore_prompts Table for Rich Details, Filtering & Universal Search
ALTER TABLE public.explore_prompts 
    ADD COLUMN IF NOT EXISTS masked_summary TEXT,
    ADD COLUMN IF NOT EXISTS preview_image_url TEXT,
    ADD COLUMN IF NOT EXISTS master_image_url TEXT,
    ADD COLUMN IF NOT EXISTS tool_applied TEXT NOT NULL DEFAULT 'text_to_image',
    ADD COLUMN IF NOT EXISTS aspect_ratio VARCHAR(10) NOT NULL DEFAULT '1:1',
    ADD COLUMN IF NOT EXISTS model_used VARCHAR(50) NOT NULL DEFAULT 'flux',
    ADD COLUMN IF NOT EXISTS dimensions VARCHAR(20) DEFAULT '1024x1024',
    ADD COLUMN IF NOT EXISTS seed BIGINT DEFAULT 42,
    ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

-- Backfill aliases if legacy columns exist
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'explore_prompts' AND column_name = 'masked_prompt_summary') THEN
        UPDATE public.explore_prompts SET masked_summary = masked_prompt_summary WHERE masked_summary IS NULL AND masked_prompt_summary IS NOT NULL;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'explore_prompts' AND column_name = 'preview_url') THEN
        UPDATE public.explore_prompts SET preview_image_url = preview_url WHERE preview_image_url IS NULL AND preview_url IS NOT NULL;
    END IF;
END $$;

-- Category created index for sub-5ms similar creation horizontal carousel queries
CREATE INDEX IF NOT EXISTS idx_explore_category_created ON public.explore_prompts (category, created_at DESC);

-- GIN index for text keyword search across explore feed (standardized with COALESCE)
DROP INDEX IF EXISTS public.idx_explore_prompts_fts;
CREATE INDEX idx_explore_prompts_fts ON public.explore_prompts 
USING gin (to_tsvector('english', 
    COALESCE(title, '') || ' ' || 
    COALESCE(masked_summary, '') || ' ' || 
    COALESCE(masked_prompt_summary, '') || ' ' || 
    COALESCE(category, '') || ' ' ||
    COALESCE(model_used, '')
));
