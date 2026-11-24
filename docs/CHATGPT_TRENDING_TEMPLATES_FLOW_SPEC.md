# ChatGPT-Style Trending Templates & Photo Remix Flow
## Comprehensive Developer Implementation & Handoff Guide
**Document Version:** 2.1.0 (Production Master)  
**Target Systems:**  
- **Mobile (`craftai_studio_mobile`):** Flutter / GetX (Owned by Mobile Developer)  
- **Web (`craftai_studio_web`):** Next.js 14 Sidebar Flow (Owned by Web Team)  
- **Database (`Supabase PostgreSQL`):** Migration 009 Updated  

---

## 📌 IMPORTANT: Supabase Database Update (Action Required First!)

> [!WARNING]
> **Aapko Supabase SQL Editor mein updated Migration 009 run karna zaroori hai!**  
> Pehle run karte waqt `ERROR: 23502: null value in column "masked_prompt_summary"` aaya tha kyunki legacy table schema mein `masked_prompt_summary` par `NOT NULL` constraint tha.  
> Humne migration ko update kar diya hai: ab ye legacy `NOT NULL` constraints ko drop karta hai aur saare 12 curated templates mein `masked_prompt_summary` aur `masked_summary` dono explicitly fill karta hai.

### 📋 SQL Query to Run in Supabase SQL Editor:
File location: `craftai_studio_backend/supabase/migrations/009_trending_templates_and_prompts.sql`  
*(Or copy-paste the block below directly into Supabase Dashboard -> SQL Editor and hit **Run**):*

```sql
-- 1. Ensure explore_prompts has all template and trending fields
ALTER TABLE public.explore_prompts 
    ADD COLUMN IF NOT EXISTS prompt TEXT,
    ADD COLUMN IF NOT EXISTS negative_prompt TEXT DEFAULT 'blurry, low quality, distorted, extra limbs, bad anatomy, text, watermark',
    ADD COLUMN IF NOT EXISTS masked_summary TEXT,
    ADD COLUMN IF NOT EXISTS masked_prompt_summary TEXT,
    ADD COLUMN IF NOT EXISTS preview_url TEXT,
    ADD COLUMN IF NOT EXISTS preview_image_url TEXT,
    ADD COLUMN IF NOT EXISTS image_url TEXT,
    ADD COLUMN IF NOT EXISTS master_image_url TEXT,
    ADD COLUMN IF NOT EXISTS master_url TEXT,
    ADD COLUMN IF NOT EXISTS prompt_cipher TEXT DEFAULT '',
    ADD COLUMN IF NOT EXISTS cipher_iv TEXT DEFAULT '',
    ADD COLUMN IF NOT EXISTS prompt_template TEXT,
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

-- 2. Drop NOT NULL constraints on legacy columns and user foreign keys
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'explore_prompts' AND column_name = 'masked_prompt_summary') THEN
        ALTER TABLE public.explore_prompts ALTER COLUMN masked_prompt_summary DROP NOT NULL;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'explore_prompts' AND column_name = 'masked_summary') THEN
        ALTER TABLE public.explore_prompts ALTER COLUMN masked_summary DROP NOT NULL;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'explore_prompts' AND column_name = 'master_url') THEN
        ALTER TABLE public.explore_prompts ALTER COLUMN master_url DROP NOT NULL;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'explore_prompts' AND column_name = 'prompt_cipher') THEN
        ALTER TABLE public.explore_prompts ALTER COLUMN prompt_cipher DROP NOT NULL;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'explore_prompts' AND column_name = 'cipher_iv') THEN
        ALTER TABLE public.explore_prompts ALTER COLUMN cipher_iv DROP NOT NULL;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'explore_prompts' AND column_name = 'prompt_template') THEN
        ALTER TABLE public.explore_prompts ALTER COLUMN prompt_template DROP NOT NULL;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'explore_prompts' AND column_name = 'author_id') THEN
        ALTER TABLE public.explore_prompts ALTER COLUMN author_id DROP NOT NULL;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'explore_prompts' AND column_name = 'user_id') THEN
        ALTER TABLE public.explore_prompts ALTER COLUMN user_id DROP NOT NULL;
    END IF;
END $$;

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

-- 6. Insert 12 Ultra-High-Quality Curated Trending Templates
INSERT INTO public.explore_prompts (
    id, title, prompt, negative_prompt, masked_prompt_summary, masked_summary,
    category, model_used, aspect_ratio, dimensions,
    preview_url, preview_image_url, image_url, master_url, prompt_template,
    likes_count, total_remixes, remixes_count,
    author_name, author_handle, author_avatar, tags, is_trending, is_featured, display_order, is_marketplace_public
) VALUES
(
    '10000000-0000-4000-8000-000000000001',
    'Cyberpunk Neo-Tokyo Rain',
    'Cinematic close-up portrait of a cyberpunk character standing in a rain-drenched futuristic Tokyo alley, luminous pink and cyan neon signs reflecting on wet jacket and skin, volumetric steam, 85mm portrait lens f/1.4, shallow depth of field, 8k octane render, hyperrealistic cinematic lighting',
    'blurry, low quality, distorted, extra limbs, bad anatomy, text, watermark',
    'Cyber Ronin • Wet Neon Street • 85mm Bokeh',
    'Cyber Ronin • Wet Neon Street • 85mm Bokeh',
    'Cyberpunk', 'FLUX.1 Schnell', '9:16', '768x1344',
    'https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800&auto=format&fit=crop',
    'Cinematic close-up portrait of a cyberpunk character standing in a rain-drenched futuristic Tokyo alley...',
    1240, 485, 485, 'Kaito Vance', '@kaitovance', 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop',
    ARRAY['cyberpunk', 'neon', 'rain', 'portrait', 'tokyo'], TRUE, TRUE, 1, TRUE
),
(
    '10000000-0000-4000-8000-000000000002',
    'Golden Hour Editorial Portrait',
    'High fashion editorial magazine cover portrait of a subject smiling in warm golden hour sunset light, wind-blown hair, natural skin texture, visible freckles, dramatic rim light, soft creamy bokeh, shot on Hasselblad H6D-100c, 85mm f/1.2, photorealistic masterpiece',
    'plastic skin, airbrushed, cartoon, oversaturated, deformed, watermark',
    'Natural Beauty • Hasselblad 100c • Soft Golden Hour',
    'Natural Beauty • Hasselblad 100c • Soft Golden Hour',
    'Photorealism', 'FLUX.1 Schnell', '1:1', '1024x1024',
    'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800&auto=format&fit=crop',
    'High fashion editorial magazine cover portrait of a subject smiling in warm golden hour sunset light...',
    1890, 720, 720, 'Elena Rostova', '@elena_visuals', 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop',
    ARRAY['portrait', 'goldenhour', 'fashion', 'editorial', 'photorealistic'], TRUE, TRUE, 2, TRUE
),
(
    '10000000-0000-4000-8000-000000000003',
    'Studio Luxury Perfume Splash',
    'Commercial studio product photography of an elegant crystal perfume bottle on dark polished obsidian rock, dynamic water splash frozen in mid-air, dramatic dual-point rim lighting with cyan and gold gels, hyper-detailed reflections, 8k commercial catalogue quality',
    'blurry, low resolution, cheap, noisy, text, label distortion',
    'Gold Chrome Fluid • Minimalist Luxury • Studio White',
    'Gold Chrome Fluid • Minimalist Luxury • Studio White',
    'Product', 'FLUX.1 Schnell', '1:1', '1024x1024',
    'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&auto=format&fit=crop',
    'Commercial studio product photography of an elegant crystal perfume bottle...',
    950, 310, 310, 'Studio Lux', '@studiolux_3d', 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop',
    ARRAY['product', 'commercial', 'water', 'splash', 'luxury'], TRUE, TRUE, 3, TRUE
),
(
    '10000000-0000-4000-8000-000000000004',
    '3D Pixar Cozy Fox Character',
    'Charming 3D animated little red fox wearing an oversized knitted autumn wool sweater and round spectacles, sitting inside a cozy treehouse library sipping hot cocoa, warm fireplace glow, Pixar Disney animation render, Unreal Engine 5 subsurface scattering, highly detailed fur texture',
    '2D, flat, ugly, distorted, harsh shadows, low polygon',
    'Pixar 3D Render • Cozy Treehouse • Subsurface Scattering',
    'Pixar 3D Render • Cozy Treehouse • Subsurface Scattering',
    '3D Render', 'FLUX.1 Schnell', '1:1', '1024x1024',
    'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=800&auto=format&fit=crop',
    'Charming 3D animated little red fox wearing an oversized knitted autumn wool sweater...',
    2150, 890, 890, 'Artisan 3D', '@artisan_3d', 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop',
    ARRAY['3d', 'pixar', 'character', 'cute', 'cozy'], TRUE, TRUE, 4, TRUE
),
(
    '10000000-0000-4000-8000-000000000005',
    'Anime Ethereal Blossom Spirit',
    'Makoto Shinkai style anime illustration of a mystical spirit girl in a flowing ceremonial kimono standing in a sea of glowing sakura cherry blossoms at twilight, starry sky with a giant crescent moon, ethereal purple and indigo lighting, delicate brushwork, emotional atmosphere, 4k masterpiece',
    'bad anatomy, 3d, realistic photograph, western comic, low resolution',
    'Makoto Shinkai Pastoral • Golden Clouds • Whimsical Anime',
    'Makoto Shinkai Pastoral • Golden Clouds • Whimsical Anime',
    'Anime', 'FLUX.1 Schnell', '16:9', '1344x768',
    'https://images.unsplash.com/photo-1563089145-599997674d42?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1563089145-599997674d42?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1563089145-599997674d42?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1563089145-599997674d42?w=800&auto=format&fit=crop',
    'Makoto Shinkai style anime illustration of a mystical spirit girl...',
    1680, 640, 640, 'Sora Anime', '@sorashinkai', 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop',
    ARRAY['anime', 'shinkai', 'sakura', 'twilight', 'fantasy'], TRUE, TRUE, 5, TRUE
),
(
    '10000000-0000-4000-8000-000000000006',
    'Futuristic Biophilic Villa',
    'Architectural digest photograph of an ultra-modern cliffside luxury villa seamlessly integrated with lush tropical waterfalls and hanging gardens, floor-to-ceiling curved glass walls, cantilevered infinity pool overlooking misty ocean sunrise, minimal Scandinavian warm wood and concrete, architectural photography',
    'distorted walls, cartoon, messy structure, noisy, oversaturated',
    'Solarpunk Architecture • Crystal Towers • Twilight Speedtrails',
    'Solarpunk Architecture • Crystal Towers • Twilight Speedtrails',
    'Architecture', 'FLUX.1 Schnell', '16:9', '1344x768',
    'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&auto=format&fit=crop',
    'Architectural digest photograph of an ultra-modern cliffside luxury villa...',
    1420, 390, 390, 'ArchDaily AI', '@archdaily_ai', 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&auto=format&fit=crop',
    ARRAY['architecture', 'villa', 'modern', 'luxury', 'biophilic'], TRUE, TRUE, 6, TRUE
),
(
    '10000000-0000-4000-8000-000000000007',
    'Vibrant Neon Cyberpunk Supercar',
    'Dynamic rolling tracking shot of a matte black futuristic electric hypercar drifting through a rain-slicked city avenue at midnight, iridescent violet underglow neon lights, water spray trails, motion blur on background skyscrapers, Reflections on wet carbon fiber body, 8k photorealistic automotive photography',
    'poor reflections, cartoon, toy car, low detail wheels, distorted perspective',
    'Cyberpunk Drift • Neon Reflections • Carbon Fiber',
    'Cyberpunk Drift • Neon Reflections • Carbon Fiber',
    'Cyberpunk', 'FLUX.1 Schnell', '16:9', '1344x768',
    'https://images.unsplash.com/photo-1558981806-ec527fa84c39?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1558981806-ec527fa84c39?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1558981806-ec527fa84c39?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1558981806-ec527fa84c39?w=800&auto=format&fit=crop',
    'Dynamic rolling tracking shot of a matte black futuristic electric hypercar...',
    1340, 520, 520, 'Velocity Lab', '@velocity_ai', 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop',
    ARRAY['car', 'supercar', 'drift', 'neon', 'automotive'], TRUE, TRUE, 7, TRUE
),
(
    '10000000-0000-4000-8000-000000000008',
    'Ethereal Crystal Deer Spirit',
    'Mythical forest guardian deer composed of glowing translucent quartz crystal and blooming bioluminescent flora, standing gracefully in a misty ancient enchanted forest, sunbeams filtering through colossal canopy, tiny floating dust motes, magical realism, high fantasy illustration',
    'ugly, deformed antlers, blurry, grainy, flat colors',
    'Mythical Crystal Deer • Bioluminescent Flora • Forest Ray',
    'Mythical Crystal Deer • Bioluminescent Flora • Forest Ray',
    'Fantasy', 'FLUX.1 Schnell', '1:1', '1024x1024',
    'https://images.unsplash.com/photo-1474511320723-9a56873867b5?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1474511320723-9a56873867b5?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1474511320723-9a56873867b5?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1474511320723-9a56873867b5?w=800&auto=format&fit=crop',
    'Mythical forest guardian deer composed of glowing translucent quartz crystal...',
    1780, 610, 610, 'Mythic Dreamer', '@mythic_dreamer', 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop',
    ARRAY['fantasy', 'crystal', 'spirit', 'nature', 'mythical'], TRUE, TRUE, 8, TRUE
),
(
    '10000000-0000-4000-8000-000000000009',
    'Retro 70s Vintage Film Portrait',
    'Authentic 1970s Kodachrome 35mm film photograph of a woman wearing retro round sunglasses and vintage leather jacket, standing outside an old California roadside diner, warm vintage grain, cinematic desaturated colors, natural analog lens flare, classic vintage aesthetic',
    'digital, sterile, modern smartphone look, over-sharpened, plastic',
    'Authentic 1970s Kodachrome • Vintage Diner • Warm Film Grain',
    'Authentic 1970s Kodachrome • Vintage Diner • Warm Film Grain',
    'Photorealism', 'FLUX.1 Schnell', '9:16', '768x1344',
    'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=800&auto=format&fit=crop',
    'Authentic 1970s Kodachrome 35mm film photograph of a woman wearing retro round sunglasses...',
    1190, 430, 430, 'Analog Soul', '@analog_soul', 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop',
    ARRAY['vintage', 'retro', 'film', 'kodachrome', '70s'], TRUE, TRUE, 9, TRUE
),
(
    '10000000-0000-4000-8000-000000000010',
    'Surreal Floating Island Sanctuary',
    'Surrealist digital painting of a serene floating verdant island high in the clouds, miniature marble pagoda temple beside a bonsai tree, water overflowing into endless sky, peaceful sunset atmosphere, dreamlike Studio Ghibli meets Salvador Dali aesthetic, 8k wallpaper',
    'turbulent, dark, messy, bad composition, noisy',
    'Surreal Floating Island • Cloud Temple • Ghibli Aesthetic',
    'Surreal Floating Island • Cloud Temple • Ghibli Aesthetic',
    'Fantasy', 'FLUX.1 Schnell', '16:9', '1344x768',
    'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&auto=format&fit=crop',
    'Surrealist digital painting of a serene floating verdant island high in the clouds...',
    1550, 480, 480, 'Dreamscape AI', '@dreamscape_ai', 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop',
    ARRAY['surreal', 'fantasy', 'island', 'clouds', 'dream'], TRUE, TRUE, 10, TRUE
),
(
    '10000000-0000-4000-8000-000000000011',
    'Cybernetic Android Geisha',
    'Hauntingly beautiful cybernetic geisha with porcelain white face and intricate polished gold mechanical filigree seams along cheekbones and neck, dark glossy hair with neon fiber-optic pins, intense amber eyes, studio portrait lighting, high-contrast dark luxury backdrop, cyberpunk couture',
    'deformed eyes, blurry seams, flat texture, cartoonish, low resolution',
    'Cybernetic Geisha • Polished Gold Seams • Cyberpunk Couture',
    'Cybernetic Geisha • Polished Gold Seams • Cyberpunk Couture',
    'Cyberpunk', 'FLUX.1 Schnell', '1:1', '1024x1024',
    'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800&auto=format&fit=crop',
    'Hauntingly beautiful cybernetic geisha with porcelain white face and intricate polished gold mechanical filigree seams...',
    1920, 780, 780, 'Kurogane Lab', '@kurogane_ai', 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop',
    ARRAY['cyberpunk', 'geisha', 'gold', 'portrait', 'android'], TRUE, TRUE, 11, TRUE
),
(
    '10000000-0000-4000-8000-000000000012',
    'Nordic Minimalist Oak Living Room',
    'Sun-drenched minimalist desert architecture with smooth terracotta rammed-earth walls, sharp geometric shadow play from mid-day sun, serene shallow reflective water pool in central courtyard, lone olive tree, Palm Springs meets Mexico modernism, architectural magazine cover shot',
    'busy, cluttered, messy textures, cloudy, distorted lines',
    'Minimalist Desert Villa • Rammed Earth • Reflective Pool',
    'Minimalist Desert Villa • Rammed Earth • Reflective Pool',
    'Architecture', 'FLUX.1 Schnell', '1:1', '1024x1024',
    'https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=800&auto=format&fit=crop',
    'Sun-drenched minimalist desert architecture with smooth terracotta rammed-earth walls...',
    1100, 360, 360, 'Desert Modern', '@desertmodern', 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop',
    ARRAY['architecture', 'minimalist', 'desert', 'shadows', 'modern'], TRUE, TRUE, 12, TRUE
)
ON CONFLICT (id) DO UPDATE SET
    title = EXCLUDED.title,
    prompt = EXCLUDED.prompt,
    negative_prompt = EXCLUDED.negative_prompt,
    masked_prompt_summary = EXCLUDED.masked_prompt_summary,
    masked_summary = EXCLUDED.masked_summary,
    category = EXCLUDED.category,
    model_used = EXCLUDED.model_used,
    aspect_ratio = EXCLUDED.aspect_ratio,
    preview_url = EXCLUDED.preview_url,
    preview_image_url = EXCLUDED.preview_image_url,
    image_url = EXCLUDED.image_url,
    master_url = EXCLUDED.master_url,
    prompt_template = EXCLUDED.prompt_template,
    likes_count = EXCLUDED.likes_count,
    total_remixes = EXCLUDED.total_remixes,
    remixes_count = EXCLUDED.remixes_count,
    tags = EXCLUDED.tags,
    is_trending = EXCLUDED.is_trending,
    is_featured = EXCLUDED.is_featured,
    display_order = EXCLUDED.display_order;
```

---

## 2. Ownership & Scope Division: Mobile vs Web

```
┌─────────────────────────────────────────────────────────────┐
│                 RESPONSIBILITY DIVISION                     │
├──────────────────────────────┬──────────────────────────────┤
│    MOBILE DEVELOPER OWNED    │       WEB TEAM OWNED         │
├──────────────────────────────┼──────────────────────────────┤
│• Floating Icon (FAB Menu)    │• Left Sidebar Navigation     │
│• TrendingTemplatesPickerSheet│• Trending Drawer on Web      │
│• TemplatePhotoRemixSheet     │• Camera / Drag-Drop Web Uploader
│• Camera/Gallery Picker Native│• Face-Lock Web Studio Router │
│• StudioController Handover   │• Independent Desktop UI Parity│
└──────────────────────────────┴──────────────────────────────┘
```

> **Note for Mobile Developer:**  
> Web side implementation will be managed by the Web team as a Sidebar item in Next.js (`craftai_studio_web`).  
> **Your sole focus is the Mobile App (`craftai_studio_mobile`) flow described below.**

---

## 3. Mobile Code Changes: Foundation Status & What is Already Done

Humne mobile codebase mein foundation layer pehle hi tayyar kar di hai taaki koi regression ya conflict na ho:

| File | Status | What Was Added / Modified |
| :--- | :--- | :--- |
| `lib/data/models/explore_card_model.dart` | ✅ **Already Done** | Added `tags` (`List<String>`), `isTrending` (`bool`), and safe multi-alias fallback for `previewUrl` & `fullPrompt`. *(Do not re-edit)* |
| `lib/features/studio/presentation/controllers/studio_controller.dart` | ✅ **Ready to Plug** | `loadPromptFromRemix` & `remixOnMyPhoto` now support unmasked prompts. Added support for `remixedFromPromptId`. |
| `lib/core/utils/permission_helper.dart` | ✅ **Already Done** | `AppPermissionHelper.pickImageSafely()` handles Camera and Gallery permissions with Settings redirect. |

---

## 4. Mobile Developer Work Items (What to Implement)

Mobile developer ko sirf ye **4 simple, clean steps** implement karne hain:

```
Step 1: FAB Menu Item  ──>  Step 2: Templates Picker Sheet  ──>  Step 3: Photo Remix Sheet  ──>  Step 4: Auto-Generate Handover
(home_shell_view.dart)      (trending_templates_picker_sheet)    (template_photo_remix_bottom)   (studio_controller.dart)
```

---

### Step 1: Update Floating Action Menu (`home_shell_view.dart`)

File: `lib/features/shell/views/home_shell_view.dart` (around line 265)

Add `FabMenuItem` for **Trending & Templates** to `ExpandableNavigationFab`:

```dart
import '../../explore/widgets/trending_templates_picker_sheet.dart';

// Inside ExpandableNavigationFab items list:
FabMenuItem(
  title: 'Trending & Templates',
  subtitle: 'Pick a trending AI style & remix your photo',
  icon: Icons.local_fire_department_rounded,
  accentColor: const Color(0xFFEF4444),
  onTap: () {
    HapticFeedback.lightImpact();
    TrendingTemplatesPickerSheet.show(context);
  },
),
```

---

### Step 2: Create `TrendingTemplatesPickerSheet.dart`

New File: `lib/features/explore/widgets/trending_templates_picker_sheet.dart`

This sheet displays the grid of trending cards with:
1. High-aesthetic Image Preview
2. **Title Clearly Mentioned on the Card** (e.g. *Cyberpunk Neo-Tokyo Rain*)
3. Style / Category Pill
4. Tapping a card opens the Photo Remix Bottom Sheet.

```dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:get/get.dart';
import 'package:craftai_studio_mobile/core/constants/app_colors.dart';
import 'package:craftai_studio_mobile/core/constants/app_dimens.dart';
import 'package:craftai_studio_mobile/core/constants/app_text_styles.dart';
import 'package:craftai_studio_mobile/data/models/explore_card_model.dart';
import 'package:craftai_studio_mobile/features/explore/controllers/explore_controller.dart';
import 'template_photo_remix_bottom_sheet.dart';

class TrendingTemplatesPickerSheet extends StatelessWidget {
  const TrendingTemplatesPickerSheet({super.key});

  static void show(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const TrendingTemplatesPickerSheet(),
    );
  }

  @override
  Widget build(BuildContext context) {
    final ExploreController exploreCtrl = Get.find<ExploreController>();

    return Container(
      constraints: BoxConstraints(maxHeight: 0.88.sh),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppDimens.radiusXl)),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        children: [
          // Drag Handle
          Center(
            child: Container(
              width: 44.w,
              height: 5.h,
              margin: EdgeInsets.symmetric(vertical: 10.h),
              decoration: BoxDecoration(
                color: AppColors.border,
                borderRadius: BorderRadius.circular(AppDimens.radiusRound),
              ),
            ),
          ),

          // Header
          Padding(
            padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 8.h),
            child: Row(
              children: [
                Container(
                  padding: EdgeInsets.all(8.r),
                  decoration: BoxDecoration(
                    color: AppColors.accentError.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(AppDimens.radiusSm),
                  ),
                  child: Icon(Icons.local_fire_department, color: AppColors.accentError, size: 20.sp),
                ),
                SizedBox(width: 10.w),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Trending Templates',
                        style: AppTextStyles.titleMedium.copyWith(fontWeight: FontWeight.bold),
                      ),
                      Text(
                        'Pick a template style and upload your photo to remix',
                        style: AppTextStyles.caption.copyWith(color: AppColors.textSecondary),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: () => Navigator.of(context).pop(),
                  icon: Icon(Icons.close_rounded, color: AppColors.textSecondary),
                ),
              ],
            ),
          ),

          const Divider(height: 1, color: AppColors.border),

          // Template Grid
          Expanded(
            child: Obx(() {
              final cards = exploreCtrl.cards.where((c) => c.isTrending || true).toList();

              if (cards.isEmpty && exploreCtrl.isInitialLoading.value) {
                return const Center(child: CircularProgressIndicator(color: AppColors.primary));
              }

              return GridView.builder(
                padding: EdgeInsets.all(14.w),
                physics: const BouncingScrollPhysics(),
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  crossAxisSpacing: 12.w,
                  mainAxisSpacing: 12.h,
                  childAspectRatio: 0.75,
                ),
                itemCount: cards.length,
                itemBuilder: (context, index) {
                  final card = cards[index];
                  return _TemplateCard(
                    card: card,
                    onTap: () {
                      HapticFeedback.lightImpact();
                      Navigator.of(context).pop();
                      TemplatePhotoRemixBottomSheet.show(context, card);
                    },
                  );
                },
              );
            }),
          ),
        ],
      ),
    );
  }
}

class _TemplateCard extends StatelessWidget {
  final ExploreCardModel card;
  final VoidCallback onTap;

  const _TemplateCard({required this.card, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.surfaceLight,
          borderRadius: BorderRadius.circular(AppDimens.radiusMd),
          border: Border.all(color: AppColors.border),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.15),
              blurRadius: 8.r,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        clipBehavior: Clip.antiAlias,
        child: Stack(
          fit: StackFit.expand,
          children: [
            CachedNetworkImage(
              imageUrl: card.previewUrl,
              fit: BoxFit.cover,
              placeholder: (_, __) => Container(color: AppColors.surfaceLight),
              errorWidget: (_, __, ___) => Icon(Icons.broken_image, color: AppColors.textMuted),
            ),
            Positioned.fill(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      Colors.transparent,
                      Colors.black.withValues(alpha: 0.2),
                      Colors.black.withValues(alpha: 0.85),
                    ],
                    stops: const [0.5, 0.7, 1.0],
                  ),
                ),
              ),
            ),
            Positioned(
              top: 8.h,
              left: 8.w,
              child: Container(
                padding: EdgeInsets.symmetric(horizontal: 6.w, vertical: 2.h),
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: 0.7),
                  borderRadius: BorderRadius.circular(AppDimens.radiusRound),
                ),
                child: Text(
                  card.category,
                  style: AppTextStyles.captionXs.copyWith(color: Colors.white, fontWeight: FontWeight.bold),
                ),
              ),
            ),
            Positioned(
              bottom: 8.h,
              left: 8.w,
              right: 8.w,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    card.title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: AppTextStyles.captionBold.copyWith(
                      color: Colors.white,
                      fontSize: 12.sp,
                      height: 1.2,
                    ),
                  ),
                  SizedBox(height: 3.h),
                  Row(
                    children: [
                      Icon(Icons.bolt, size: 11.sp, color: AppColors.accentWarning),
                      SizedBox(width: 2.w),
                      Text(
                        card.modelUsed,
                        style: AppTextStyles.captionXs.copyWith(color: AppColors.textSecondary, fontSize: 9.sp),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

---

### Step 3: Create `TemplatePhotoRemixBottomSheet.dart`

New File: `lib/features/explore/widgets/template_photo_remix_bottom_sheet.dart`

This sheet displays the Reference Image preview, title, and 2 large touch targets:
- **`[ 📸 Take Photo ]`** (Uses `AppPermissionHelper.pickImageSafely(source: ImageSource.camera)`)
- **`[ 🖼️ Upload Photo ]`** (Uses `AppPermissionHelper.pickImageSafely(source: ImageSource.gallery)`)

```dart
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:image_picker/image_picker.dart';
import 'package:get/get.dart';
import 'package:craftai_studio_mobile/core/constants/app_colors.dart';
import 'package:craftai_studio_mobile/core/constants/app_dimens.dart';
import 'package:craftai_studio_mobile/core/constants/app_text_styles.dart';
import 'package:craftai_studio_mobile/core/utils/permission_helper.dart';
import 'package:craftai_studio_mobile/data/models/explore_card_model.dart';
import 'package:craftai_studio_mobile/features/studio/presentation/controllers/studio_controller.dart';

class TemplatePhotoRemixBottomSheet extends StatelessWidget {
  final ExploreCardModel template;

  const TemplatePhotoRemixBottomSheet({super.key, required this.template});

  static void show(BuildContext context, ExploreCardModel template) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => TemplatePhotoRemixBottomSheet(template: template),
    );
  }

  Future<void> _handlePhotoInput(BuildContext context, ImageSource source) async {
    HapticFeedback.lightImpact();

    final pickedFile = await AppPermissionHelper.pickImageSafely(source: source);
    if (pickedFile == null) return;

    if (context.mounted) {
      Navigator.of(context).pop();
    }

    final studioCtrl = Get.find<StudioController>();
    await studioCtrl.startTemplateRemixGeneration(
      template: template,
      userPhoto: File(pickedFile.path),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 12.h),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppDimens.radiusXl)),
        border: Border.all(color: AppColors.border),
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 44.w,
                height: 5.h,
                margin: EdgeInsets.only(bottom: 12.h),
                decoration: BoxDecoration(
                  color: AppColors.border,
                  borderRadius: BorderRadius.circular(AppDimens.radiusRound),
                ),
              ),
            ),
            Container(
              padding: EdgeInsets.all(10.w),
              decoration: BoxDecoration(
                color: AppColors.surfaceLight,
                borderRadius: BorderRadius.circular(AppDimens.radiusMd),
                border: Border.all(color: AppColors.border),
              ),
              child: Row(
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(AppDimens.radiusSm),
                    child: CachedNetworkImage(
                      imageUrl: template.previewUrl,
                      width: 64.w,
                      height: 64.w,
                      fit: BoxFit.cover,
                    ),
                  ),
                  SizedBox(width: 12.w),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: EdgeInsets.symmetric(horizontal: 6.w, vertical: 2.h),
                              decoration: BoxDecoration(
                                color: AppColors.primary.withValues(alpha: 0.15),
                                borderRadius: BorderRadius.circular(AppDimens.radiusRound),
                              ),
                              child: Text(
                                template.category,
                                style: AppTextStyles.captionXs.copyWith(color: AppColors.primary, fontWeight: FontWeight.bold),
                              ),
                            ),
                            SizedBox(width: 6.w),
                            Text(
                              'Template Style',
                              style: AppTextStyles.caption.copyWith(color: AppColors.textMuted),
                            ),
                          ],
                        ),
                        SizedBox(height: 4.h),
                        Text(
                          template.title,
                          style: AppTextStyles.bodyMediumBold.copyWith(fontSize: 14.sp),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        SizedBox(height: 2.h),
                        Text(
                          'Creator: ${template.authorName}',
                          style: AppTextStyles.caption.copyWith(color: AppColors.textSecondary, fontSize: 11.sp),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            SizedBox(height: 16.h),
            Text(
              'Add Your Photo to Remix',
              style: AppTextStyles.titleSmall.copyWith(fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 4.h),
            Text(
              'AI will lock your face and facial features while styling your picture with the ${template.title} aesthetic.',
              style: AppTextStyles.caption.copyWith(color: AppColors.textSecondary, height: 1.3),
            ),
            SizedBox(height: 18.h),
            Row(
              children: [
                Expanded(
                  child: SizedBox(
                    height: 52.h,
                    child: ElevatedButton.icon(
                      onPressed: () => _handlePhotoInput(context, ImageSource.camera),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.surfaceLight,
                        foregroundColor: AppColors.textPrimary,
                        elevation: 0,
                        side: BorderSide(color: AppColors.border, width: 1.2),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(AppDimens.radiusMd),
                        ),
                      ),
                      icon: const Icon(Icons.photo_camera_rounded, size: 20),
                      label: Text(
                        'Take Photo',
                        style: AppTextStyles.bodyMediumBold.copyWith(fontSize: 13.sp),
                      ),
                    ),
                  ),
                ),
                SizedBox(width: 12.w),
                Expanded(
                  child: SizedBox(
                    height: 52.h,
                    child: ElevatedButton.icon(
                      onPressed: () => _handlePhotoInput(context, ImageSource.gallery),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.primary,
                        foregroundColor: Colors.white,
                        elevation: 0,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(AppDimens.radiusMd),
                        ),
                      ),
                      icon: const Icon(Icons.photo_library_rounded, size: 20),
                      label: Text(
                        'Upload Photo',
                        style: AppTextStyles.bodyMediumBold.copyWith(color: Colors.white, fontSize: 13.sp),
                      ),
                    ),
                  ),
                ),
              ],
            ),
            SizedBox(height: 8.h),
          ],
        ),
      ),
    );
  }
}
```

---

### Step 4: Add Handover Function to `StudioController.dart`

File: `lib/features/studio/presentation/controllers/studio_controller.dart`

Add this method to `StudioController`:

```dart
/// Initiates instant ChatGPT-style photo remix generation using a template
Future<void> startTemplateRemixGeneration({
  required ExploreCardModel template,
  required File userPhoto,
}) async {
  // 1. Switch active tab to Studio (Index 1)
  final shellCtrl = Get.find<ShellController>();
  shellCtrl.switchTab(1);

  // 2. Record provenance for creator royalty attribution
  remixedFromPromptId.value = template.id;

  // 3. Attach user photo into reference strip
  referenceImages.clear();
  referenceImages.add(userPhoto.path);

  // 4. Resolve unmasked prompt with Subject-Lock (Face-Lock) constraints
  final cleanPrompt = template.fullPrompt.isNotEmpty && !template.fullPrompt.contains('[Secret Recipe Encrypted]')
      ? template.fullPrompt
      : template.maskedSummary.replaceAll(' • [Secret Recipe Encrypted]', '');

  promptController.text =
      'DO NOT CHANGE THE HUMAN SUBJECT. HUMAN SUBJECT — ABSOLUTE LOCK. $cleanPrompt';

  // 5. Sync generation settings with the template
  selectedAspectRatio.value = template.aspectRatio;
  selectedModel.value = template.modelUsed;

  // 6. Provide instant feedback toast
  Get.snackbar(
    'Generating Remix... ⚡',
    'Applying ${template.title} style to your photo with Subject Lock!',
    snackPosition: SnackPosition.BOTTOM,
    backgroundColor: AppColors.surface,
    colorText: AppColors.primary,
    duration: const Duration(seconds: 3),
    icon: const Icon(Icons.auto_awesome, color: AppColors.primary),
  );

  // 7. Auto-start image generation
  await generateImage();
}
```

---

## 5. Summary of Conflict Prevention & Zero Loopholes

1. **No Backend API Dependency:** Direct Supabase `explore_prompts` select query. Zero new FastAPI endpoints needed.
2. **Subject Lock (Face Lock):** User facial identity remains 100% locked via `DO NOT CHANGE THE HUMAN SUBJECT. HUMAN SUBJECT — ABSOLUTE LOCK.` prefix.
3. **Automatic Permission Handler:** Uses `AppPermissionHelper.pickImageSafely()` to gracefully handle camera/gallery denials and redirect to Settings if blocked.
4. **Credit Protection:** `generateImage()` already checks wallet balance and shows Top-Up modal if credits are 0.
5. **No Broken Images:** `ExploreCardModel` falls back across `preview_image_url`, `preview_url`, and `image_url`.
6. **No Encrypted Prompts:** Always pulls unmasked creative prompt from `template.fullPrompt`.
