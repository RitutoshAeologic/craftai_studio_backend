-- ==============================================================================
-- Migration 009: Trending Images, Inspiration Prompts & Template Remix Engine
-- Unified schema & rich seed data for Web and Mobile discovery parity
-- ==============================================================================

-- 1. Ensure explore_prompts has all template and trending fields
ALTER TABLE public.explore_prompts 
    ADD COLUMN IF NOT EXISTS prompt TEXT,
    ADD COLUMN IF NOT EXISTS negative_prompt TEXT DEFAULT 'blurry, low quality, distorted, extra limbs, bad anatomy, text, watermark',
    ADD COLUMN IF NOT EXISTS preview_url TEXT,
    ADD COLUMN IF NOT EXISTS preview_image_url TEXT,
    ADD COLUMN IF NOT EXISTS image_url TEXT,
    ADD COLUMN IF NOT EXISTS master_image_url TEXT,
    ADD COLUMN IF NOT EXISTS category TEXT DEFAULT 'Photorealism',
    ADD COLUMN IF NOT EXISTS model_used TEXT DEFAULT 'FLUX.1 Schnell',
    ADD COLUMN IF NOT EXISTS aspect_ratio VARCHAR(10) DEFAULT '1:1',
    ADD COLUMN IF NOT EXISTS dimensions VARCHAR(20) DEFAULT '1024x1024',
    ADD COLUMN IF NOT EXISTS seed BIGINT DEFAULT 42,
    ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS is_trending BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS is_featured BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS display_order INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS likes_count INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_remixes INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS remixes_count INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS author_name TEXT DEFAULT 'CraftAI Curated',
    ADD COLUMN IF NOT EXISTS author_handle TEXT DEFAULT '@craftai',
    ADD COLUMN IF NOT EXISTS author_avatar TEXT DEFAULT 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop',
    ADD COLUMN IF NOT EXISTS base_remix_fee NUMERIC(10, 2) DEFAULT 4.00,
    ADD COLUMN IF NOT EXISTS author_royalty_cut NUMERIC(10, 2) DEFAULT 1.60,
    ADD COLUMN IF NOT EXISTS is_marketplace_public BOOLEAN NOT NULL DEFAULT TRUE;

-- 2. Allow system/curated templates without strict user foreign key constraints
ALTER TABLE public.explore_prompts ALTER COLUMN author_id DROP NOT NULL;
ALTER TABLE public.explore_prompts ALTER COLUMN user_id DROP NOT NULL;

-- 3. Synchronize image URLs and prompt aliases across platforms
UPDATE public.explore_prompts 
SET 
    image_url = COALESCE(image_url, preview_url, preview_image_url),
    preview_url = COALESCE(preview_url, preview_image_url, image_url),
    preview_image_url = COALESCE(preview_image_url, preview_url, image_url),
    remixes_count = COALESCE(remixes_count, total_remixes, 0),
    total_remixes = COALESCE(total_remixes, remixes_count, 0)
WHERE image_url IS NULL OR preview_url IS NULL;

-- 4. Create High-Speed Indexes
CREATE INDEX IF NOT EXISTS idx_explore_trending ON public.explore_prompts (is_trending, display_order ASC);
CREATE INDEX IF NOT EXISTS idx_explore_category_trending ON public.explore_prompts (category, is_trending, created_at DESC);

-- 5. Row Level Security Policy (Public Read)
ALTER TABLE public.explore_prompts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public can view marketplace prompts" ON public.explore_prompts;
CREATE POLICY "Public can view marketplace prompts" ON public.explore_prompts 
    FOR SELECT USING (is_marketplace_public = TRUE);

GRANT ALL ON public.explore_prompts TO anon, authenticated, service_role;

-- ==============================================================================
-- 6. Insert 12 Ultra-High-Quality Curated Trending Templates
-- Real, usable, unmasked creative prompts across popular generative styles
-- ==============================================================================

INSERT INTO public.explore_prompts (
    id, title, prompt, negative_prompt, category, model_used, aspect_ratio, dimensions,
    preview_url, preview_image_url, image_url, likes_count, total_remixes, remixes_count,
    author_name, author_handle, author_avatar, tags, is_trending, is_featured, display_order, is_marketplace_public
) VALUES
(
    '10000000-0000-4000-8000-000000000001',
    'Cyberpunk Neo-Tokyo Rain',
    'Cinematic close-up portrait of a cyberpunk character standing in a rain-drenched futuristic Tokyo alley, luminous pink and cyan neon signs reflecting on wet jacket and skin, volumetric steam, 85mm portrait lens f/1.4, shallow depth of field, 8k octane render, hyperrealistic cinematic lighting',
    'blurry, low quality, distorted, extra limbs, bad anatomy, text, watermark',
    'Cyberpunk',
    'FLUX.1 Schnell',
    '9:16',
    '768x1344',
    'https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800&auto=format&fit=crop',
    1240, 485, 485,
    'Kaito Vance', '@kaitovance', 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop',
    ARRAY['cyberpunk', 'neon', 'rain', 'portrait', 'tokyo'],
    TRUE, TRUE, 1, TRUE
),
(
    '10000000-0000-4000-8000-000000000002',
    'Golden Hour Editorial Portrait',
    'High fashion editorial magazine cover portrait of a subject smiling in warm golden hour sunset light, wind-blown hair, natural skin texture, visible freckles, dramatic rim light, soft creamy bokeh, shot on Hasselblad H6D-100c, 85mm f/1.2, photorealistic masterpiece',
    'plastic skin, airbrushed, cartoon, oversaturated, deformed, watermark',
    'Photorealism',
    'FLUX.1 Schnell',
    '1:1',
    '1024x1024',
    'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800&auto=format&fit=crop',
    1890, 720, 720,
    'Elena Rostova', '@elena_visuals', 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop',
    ARRAY['portrait', 'goldenhour', 'fashion', 'editorial', 'photorealistic'],
    TRUE, TRUE, 2, TRUE
),
(
    '10000000-0000-4000-8000-000000000003',
    'Studio Luxury Perfume Splash',
    'Commercial studio product photography of an elegant crystal perfume bottle on dark polished obsidian rock, dynamic water splash frozen in mid-air, dramatic dual-point rim lighting with cyan and gold gels, hyper-detailed reflections, 8k commercial catalogue quality',
    'blurry, low resolution, cheap, noisy, text, label distortion',
    'Product',
    'FLUX.1 Schnell',
    '1:1',
    '1024x1024',
    'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&auto=format&fit=crop',
    950, 310, 310,
    'Studio Lux', '@studiolux_3d', 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop',
    ARRAY['product', 'commercial', 'water', 'splash', 'luxury'],
    TRUE, TRUE, 3, TRUE
),
(
    '10000000-0000-4000-8000-000000000004',
    '3D Pixar Cozy Fox Character',
    'Charming 3D animated little red fox wearing an oversized knitted autumn wool sweater and round spectacles, sitting inside a cozy treehouse library sipping hot cocoa, warm fireplace glow, Pixar Disney animation render, Unreal Engine 5 subsurface scattering, highly detailed fur texture',
    '2D, flat, ugly, distorted, harsh shadows, low polygon',
    '3D Render',
    'FLUX.1 Schnell',
    '1:1',
    '1024x1024',
    'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=800&auto=format&fit=crop',
    2150, 890, 890,
    'Artisan 3D', '@artisan_3d', 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop',
    ARRAY['3d', 'pixar', 'character', 'cute', 'cozy'],
    TRUE, TRUE, 4, TRUE
),
(
    '10000000-0000-4000-8000-000000000005',
    'Anime Ethereal Blossom Spirit',
    'Makoto Shinkai style anime illustration of a mystical spirit girl in a flowing ceremonial kimono standing in a sea of glowing sakura cherry blossoms at twilight, starry sky with a giant crescent moon, ethereal purple and indigo lighting, delicate brushwork, emotional atmosphere, 4k masterpiece',
    'bad anatomy, 3d, realistic photograph, western comic, low resolution',
    'Anime',
    'FLUX.1 Schnell',
    '16:9',
    '1344x768',
    'https://images.unsplash.com/photo-1563089145-599997674d42?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1563089145-599997674d42?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1563089145-599997674d42?w=800&auto=format&fit=crop',
    1680, 640, 640,
    'Sora Anime', '@sorashinkai', 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop',
    ARRAY['anime', 'shinkai', 'sakura', 'twilight', 'fantasy'],
    TRUE, TRUE, 5, TRUE
),
(
    '10000000-0000-4000-8000-000000000006',
    'Futuristic Biophilic Villa',
    'Architectural digest photograph of an ultra-modern cliffside luxury villa seamlessly integrated with lush tropical waterfalls and hanging gardens, floor-to-ceiling curved glass walls, cantilevered infinity pool overlooking misty ocean sunrise, minimal Scandinavian warm wood and concrete, architectural photography',
    'distorted walls, cartoon, messy structure, noisy, oversaturated',
    'Architecture',
    'FLUX.1 Schnell',
    '16:9',
    '1344x768',
    'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&auto=format&fit=crop',
    1420, 390, 390,
    'ArchDaily AI', '@archdaily_ai', 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&auto=format&fit=crop',
    ARRAY['architecture', 'villa', 'modern', 'luxury', 'biophilic'],
    TRUE, TRUE, 6, TRUE
),
(
    '10000000-0000-4000-8000-000000000007',
    'Vibrant Neon Cyberpunk Supercar',
    'Dynamic rolling tracking shot of a matte black futuristic electric hypercar drifting through a rain-slicked city avenue at midnight, iridescent violet underglow neon lights, water spray trails, motion blur on background skyscrapers, Reflections on wet carbon fiber body, 8k photorealistic automotive photography',
    'poor reflections, cartoon, toy car, low detail wheels, distorted perspective',
    'Cyberpunk',
    'FLUX.1 Schnell',
    '16:9',
    '1344x768',
    'https://images.unsplash.com/photo-1558981806-ec527fa84c39?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1558981806-ec527fa84c39?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1558981806-ec527fa84c39?w=800&auto=format&fit=crop',
    1340, 520, 520,
    'Velocity Lab', '@velocity_ai', 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop',
    ARRAY['car', 'supercar', 'drift', 'neon', 'automotive'],
    TRUE, TRUE, 7, TRUE
),
(
    '10000000-0000-4000-8000-000000000008',
    'Ethereal Crystal Deer Spirit',
    'Mythical forest guardian deer composed of glowing translucent quartz crystal and blooming bioluminescent flora, standing gracefully in a misty ancient enchanted forest, sunbeams filtering through colossal canopy, tiny floating dust motes, magical realism, high fantasy illustration',
    'ugly, deformed antlers, blurry, grainy, flat colors',
    'Fantasy',
    'FLUX.1 Schnell',
    '1:1',
    '1024x1024',
    'https://images.unsplash.com/photo-1474511320723-9a56873867b5?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1474511320723-9a56873867b5?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1474511320723-9a56873867b5?w=800&auto=format&fit=crop',
    1780, 610, 610,
    'Mythic Dreamer', '@mythic_dreamer', 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop',
    ARRAY['fantasy', 'crystal', 'spirit', 'nature', 'mythical'],
    TRUE, TRUE, 8, TRUE
),
(
    '10000000-0000-4000-8000-000000000009',
    'Retro 70s Vintage Film Portrait',
    'Authentic 1970s Kodachrome 35mm film photograph of a woman wearing retro round sunglasses and vintage leather jacket, standing outside an old California roadside diner, warm vintage grain, cinematic desaturated colors, natural analog lens flare, classic vintage aesthetic',
    'digital, sterile, modern smartphone look, over-sharpened, plastic',
    'Photorealism',
    'FLUX.1 Schnell',
    '9:16',
    '768x1344',
    'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=800&auto=format&fit=crop',
    1190, 430, 430,
    'Analog Soul', '@analog_soul', 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop',
    ARRAY['vintage', 'retro', 'film', 'kodachrome', '70s'],
    TRUE, TRUE, 9, TRUE
),
(
    '10000000-0000-4000-8000-000000000010',
    'Surreal Floating Island Sanctuary',
    'Surrealist digital painting of a serene floating verdant island high in the clouds, miniature marble pagoda temple beside a bonsai tree, water overflowing into endless sky, peaceful sunset atmosphere, dreamlike Studio Ghibli meets Salvador Dali aesthetic, 8k wallpaper',
    'turbulent, dark, messy, bad composition, noisy',
    'Fantasy',
    'FLUX.1 Schnell',
    '16:9',
    '1344x768',
    'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&auto=format&fit=crop',
    1550, 480, 480,
    'Dreamscape AI', '@dreamscape_ai', 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop',
    ARRAY['surreal', 'fantasy', 'island', 'clouds', 'dream'],
    TRUE, TRUE, 10, TRUE
),
(
    '10000000-0000-4000-8000-000000000011',
    'Cybernetic Android Geisha',
    'Hauntingly beautiful cybernetic geisha with porcelain white face and intricate polished gold mechanical filigree seams along cheekbones and neck, dark glossy hair with neon fiber-optic pins, intense amber eyes, studio portrait lighting, high-contrast dark luxury backdrop, cyberpunk couture',
    'deformed eyes, blurry seams, flat texture, cartoonish, low resolution',
    'Cyberpunk',
    'FLUX.1 Schnell',
    '1:1',
    '1024x1024',
    'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800&auto=format&fit=crop',
    2400, 930, 930,
    'Neo Nippon', '@neonippon', 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop',
    ARRAY['cybernetic', 'geisha', 'gold', 'cyborg', 'couture'],
    TRUE, TRUE, 11, TRUE
),
(
    '10000000-0000-4000-8000-000000000012',
    'Architectural Minimalist Desert House',
    'Sun-drenched minimalist desert architecture with smooth terracotta rammed-earth walls, sharp geometric shadow play from mid-day sun, serene shallow reflective water pool in central courtyard, lone olive tree, Palm Springs meets Mexico modernism, architectural magazine cover shot',
    'busy, cluttered, messy textures, cloudy, distorted lines',
    'Architecture',
    'FLUX.1 Schnell',
    '1:1',
    '1024x1024',
    'https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=800&auto=format&fit=crop',
    1100, 360, 360,
    'Desert Modern', '@desertmodern', 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop',
    ARRAY['architecture', 'minimalist', 'desert', 'shadows', 'modern'],
    TRUE, TRUE, 12, TRUE
)
ON CONFLICT (id) DO UPDATE SET
    title = EXCLUDED.title,
    prompt = EXCLUDED.prompt,
    negative_prompt = EXCLUDED.negative_prompt,
    category = EXCLUDED.category,
    model_used = EXCLUDED.model_used,
    aspect_ratio = EXCLUDED.aspect_ratio,
    preview_url = EXCLUDED.preview_url,
    preview_image_url = EXCLUDED.preview_image_url,
    image_url = EXCLUDED.image_url,
    likes_count = EXCLUDED.likes_count,
    total_remixes = EXCLUDED.total_remixes,
    remixes_count = EXCLUDED.remixes_count,
    tags = EXCLUDED.tags,
    is_trending = EXCLUDED.is_trending,
    is_featured = EXCLUDED.is_featured,
    display_order = EXCLUDED.display_order;
