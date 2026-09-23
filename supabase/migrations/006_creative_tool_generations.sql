-- 006_creative_tool_generations.sql
-- Dedicated ledger for all 5 MeiGen Creative Tools executions

CREATE TABLE IF NOT EXISTS public.tool_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tool_type VARCHAR(50) NOT NULL, -- "ai_background", "ai_expand", "upscale", "product_detail", "marketing_poster", "bg_removal"
    input_image_url TEXT NOT NULL,
    output_image_url TEXT,
    parameters JSONB DEFAULT '{}'::jsonb,
    credits_consumed NUMERIC(5, 2) DEFAULT 0.0,
    latency_ms INTEGER,
    status VARCHAR(20) DEFAULT 'completed',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_tool_generations_user_id ON public.tool_generations(user_id);
CREATE INDEX IF NOT EXISTS idx_tool_generations_tool_type ON public.tool_generations(tool_type);
CREATE INDEX IF NOT EXISTS idx_tool_generations_created_at ON public.tool_generations(created_at DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE public.tool_generations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can select own tool generations"
    ON public.tool_generations FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own tool generations"
    ON public.tool_generations FOR INSERT
    WITH CHECK (auth.uid() = user_id);

COMMENT ON TABLE public.tool_generations IS 'Dedicated audit ledger and generation history for Creative AI Skills';
