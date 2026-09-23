-- 005_skills_metadata.sql
-- Adds metadata JSONB column to public.jobs for MeiGen AI Skills (Backgrounds, Expand, Poster, etc.)

ALTER TABLE public.jobs 
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_jobs_user_type ON public.jobs (user_id, type, created_at DESC);

COMMENT ON COLUMN public.jobs.metadata IS 'Flexible JSONB payload for skill-specific attributes (source_image_url, mode, ratio, headline, etc.)';
