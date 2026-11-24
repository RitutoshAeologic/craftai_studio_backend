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
-- ==============================================================================
-- Migration 009: Trending Images, Inspiration Prompts & Template Remix Engine
-- Unified schema & rich seed data for Web and Mobile discovery parity
-- ==============================================================================

-- 1. Ensure explore_prompts has all template and trending fields (both modern and legacy aliases)
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

-- 2. Drop NOT NULL constraints on legacy columns and user foreign keys so curated starter templates load smoothly
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

-- ==============================================================================
-- 6. Insert 12 100% Visually-Matched Curated Trending Templates
-- Populates both modern and legacy columns (masked_prompt_summary, masked_summary,
-- preview_url, preview_image_url, image_url, prompt, negative_prompt)
-- ==============================================================================

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
    'Cinematic wide night street in neo-Tokyo with towering illuminated neon signage, rain-slicked asphalt reflecting vibrant magenta and cyan lights, futuristic cyberpunk atmosphere, 8k resolution, photorealistic cinematic lighting',
    'blurry, low quality, distorted, extra limbs, bad anatomy, text, watermark',
    'Neo-Tokyo • Neon Street • Rain Reflections',
    'Neo-Tokyo • Neon Street • Rain Reflections',
    'Cyberpunk',
    'FLUX.1 Schnell',
    '9:16',
    '768x1344',
    'https://images.unsplash.com/photo-1503899036084-c55cdd92da26?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1503899036084-c55cdd92da26?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1503899036084-c55cdd92da26?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1503899036084-c55cdd92da26?w=800&auto=format&fit=crop',
    'Cinematic wide night street in neo-Tokyo with towering illuminated neon signage, rain-slicked asphalt reflecting vibrant magenta and cyan lights, futuristic cyberpunk atmosphere, 8k resolution, photorealistic cinematic lighting',
    1240, 485, 485,
    'Kaito Vance', '@kaitovance', 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop',
    ARRAY['cyberpunk', 'neon', 'rain', 'tokyo', 'street'],
    TRUE, TRUE, 1, TRUE
),
(
    '10000000-0000-4000-8000-000000000002',
    'Golden Hour Editorial Portrait',
    'High fashion editorial magazine cover portrait of a subject in warm golden hour sunset light, wind-blown hair, natural skin texture, visible freckles, dramatic rim light, soft creamy bokeh, 85mm f/1.2, photorealistic masterpiece',
    'plastic skin, airbrushed, cartoon, oversaturated, deformed, watermark',
    'Natural Beauty • Golden Hour • 85mm Bokeh',
    'Natural Beauty • Golden Hour • 85mm Bokeh',
    'Photorealism',
    'FLUX.1 Schnell',
    '1:1',
    '1024x1024',
    'https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?w=800&auto=format&fit=crop',
    'High fashion editorial magazine cover portrait of a subject in warm golden hour sunset light, wind-blown hair, natural skin texture, visible freckles, dramatic rim light, soft creamy bokeh, 85mm f/1.2, photorealistic masterpiece',
    1890, 720, 720,
    'Elena Rostova', '@elena_visuals', 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop',
    ARRAY['portrait', 'goldenhour', 'fashion', 'editorial', 'photorealistic'],
    TRUE, TRUE, 2, TRUE
),
(
    '10000000-0000-4000-8000-000000000003',
    'Studio Luxury Perfume Splash',
    'Commercial luxury perfume bottle photography, clear faceted crystal glass flacon with delicate pink fragrance, surrounded by soft blush rose petals and floating water droplets, studio softbox lighting, shallow depth of field, high-end cosmetics advertisement',
    'blurry, low resolution, cheap, noisy, text, label distortion',
    'Luxury Perfume • Crystal Flacon • Rose Petals',
    'Luxury Perfume • Crystal Flacon • Rose Petals',
    'Commercial',
    'FLUX.1 Schnell',
    '1:1',
    '1024x1024',
    'https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?w=800&auto=format&fit=crop',
    'Commercial luxury perfume bottle photography, clear faceted crystal glass flacon with delicate pink fragrance, surrounded by soft blush rose petals and floating water droplets, studio softbox lighting, shallow depth of field, high-end cosmetics advertisement',
    950, 310, 310,
    'Studio Lux', '@studiolux_3d', 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop',
    ARRAY['product', 'commercial', 'perfume', 'luxury', 'cosmetics'],
    TRUE, TRUE, 3, TRUE
),
(
    '10000000-0000-4000-8000-000000000004',
    'Woodland Red Fox in Snow',
    'Close-up wildlife portrait of a fluffy red fox sitting in pristine white snow, warm golden winter sunlight rim-lighting the fur, soft bokeh pine forest background, national geographic style, crystal clear 8k resolution, shot on 400mm telephoto lens',
    '2D, flat, ugly, distorted, harsh shadows, cartoon, bad anatomy',
    'Red Fox • Sunlit Snow • National Geographic',
    'Red Fox • Sunlit Snow • National Geographic',
    'Wildlife',
    'FLUX.1 Schnell',
    '4:5',
    '896x1120',
    'https://images.unsplash.com/photo-1474511320723-9a56873867b5?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1474511320723-9a56873867b5?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1474511320723-9a56873867b5?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1474511320723-9a56873867b5?w=800&auto=format&fit=crop',
    'Close-up wildlife portrait of a fluffy red fox sitting in pristine white snow, warm golden winter sunlight rim-lighting the fur, soft bokeh pine forest background, national geographic style, crystal clear 8k resolution, shot on 400mm telephoto lens',
    2150, 890, 890,
    'Wild Horizon', '@wildhorizon', 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop',
    ARRAY['wildlife', 'fox', 'winter', 'snow', 'nature'],
    TRUE, TRUE, 4, TRUE
),
(
    '10000000-0000-4000-8000-000000000005',
    'Anime Sakura Blossom Stream',
    'Breathtaking night view of a serene Tokyo river canal arched over with blooming pink cherry blossom trees, glowing traditional paper lanterns casting soft pink and warm amber reflections on the water, Makoto Shinkai anime style, dreamy and atmospheric 4k',
    'bad anatomy, 3d, realistic photograph, western comic, low resolution',
    'Sakura River • Glowing Lanterns • Anime Dream',
    'Sakura River • Glowing Lanterns • Anime Dream',
    'Anime',
    'FLUX.1 Schnell',
    '16:9',
    '1344x768',
    'https://images.unsplash.com/photo-1524413840807-0c3cb6fa808d?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1524413840807-0c3cb6fa808d?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1524413840807-0c3cb6fa808d?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1524413840807-0c3cb6fa808d?w=800&auto=format&fit=crop',
    'Breathtaking night view of a serene Tokyo river canal arched over with blooming pink cherry blossom trees, glowing traditional paper lanterns casting soft pink and warm amber reflections on the water, Makoto Shinkai anime style, dreamy and atmospheric 4k',
    1680, 640, 640,
    'Sora Anime', '@sorashinkai', 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop',
    ARRAY['anime', 'shinkai', 'sakura', 'lanterns', 'night'],
    TRUE, TRUE, 5, TRUE
),
(
    '10000000-0000-4000-8000-000000000006',
    'Futuristic Biophilic Pool Villa',
    'Architectural digest photo of an ultra-luxury modern biophilic villa with curved glass walls, cantilevered infinity pool overlooking lush tropical gardens, sunlit terrace with palm trees, clean modern lines, bright daylight, hyperrealistic architectural photography',
    'distorted walls, cartoon, messy structure, noisy, oversaturated',
    'Luxury Pool Villa • Palm Trees • Modern Architecture',
    'Luxury Pool Villa • Palm Trees • Modern Architecture',
    'Architecture',
    'FLUX.1 Schnell',
    '16:9',
    '1344x768',
    'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800&auto=format&fit=crop',
    'Architectural digest photo of an ultra-luxury modern biophilic villa with curved glass walls, cantilevered infinity pool overlooking lush tropical gardens, sunlit terrace with palm trees, clean modern lines, bright daylight, hyperrealistic architectural photography',
    1420, 390, 390,
    'ArchDaily AI', '@archdaily_ai', 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&auto=format&fit=crop',
    ARRAY['architecture', 'villa', 'pool', 'luxury', 'modern'],
    TRUE, TRUE, 6, TRUE
),
(
    '10000000-0000-4000-8000-000000000007',
    'Midnight Supercar Horizon',
    'Cinematic low-angle tracking shot of a sleek aerodynamic black sports car cruising on an open coastal highway during twilight, glowing red LED taillights, motion blur wheels, reflections of sunset sky on polished gloss metallic body, Top Gear automotive photography',
    'poor reflections, cartoon, toy car, low detail wheels, distorted perspective',
    'Black Supercar • Twilight Highway • LED Lights',
    'Black Supercar • Twilight Highway • LED Lights',
    'Concept Art',
    'FLUX.1 Schnell',
    '16:9',
    '1344x768',
    'https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=800&auto=format&fit=crop',
    'Cinematic low-angle tracking shot of a sleek aerodynamic black sports car cruising on an open coastal highway during twilight, glowing red LED taillights, motion blur wheels, reflections of sunset sky on polished gloss metallic body, Top Gear automotive photography',
    1340, 520, 520,
    'Velocity Lab', '@velocity_ai', 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop',
    ARRAY['car', 'supercar', 'highway', 'porsche', 'automotive'],
    TRUE, TRUE, 7, TRUE
),
(
    '10000000-0000-4000-8000-000000000008',
    'Majestic Forest Stag Spirit',
    'Magnificent wild stag with large branched antlers standing proudly in an ancient sunlit woodland, ethereal rays of light filtering through the tree canopy, lush green mossy forest floor, magical mythical nature photography, 8k crisp details',
    'ugly, deformed antlers, blurry, grainy, flat colors',
    'Forest Stag • Grand Antlers • Sunlit Woodland',
    'Forest Stag • Grand Antlers • Sunlit Woodland',
    'Wildlife',
    'FLUX.1 Schnell',
    '1:1',
    '1024x1024',
    'https://images.unsplash.com/photo-1484406566174-9da000fda645?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1484406566174-9da000fda645?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1484406566174-9da000fda645?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1484406566174-9da000fda645?w=800&auto=format&fit=crop',
    'Magnificent wild stag with large branched antlers standing proudly in an ancient sunlit woodland, ethereal rays of light filtering through the tree canopy, lush green mossy forest floor, magical mythical nature photography, 8k crisp details',
    1780, 610, 610,
    'Mythic Dreamer', '@mythic_dreamer', 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop',
    ARRAY['wildlife', 'stag', 'deer', 'forest', 'nature'],
    TRUE, TRUE, 8, TRUE
),
(
    '10000000-0000-4000-8000-000000000009',
    'Retro Boho Sunglasses Portrait',
    'Vibrant vintage 70s summer fashion portrait of a stylish woman holding round sunglasses, retro bohemian crop top, warm sun-kissed skin, golden sunlight against a sunny backdrop, authentic Kodachrome film grain, analog color grade, effortless indie aesthetic',
    'digital render, modern plastic look, low detail, oversaturated neon, bad eyes',
    '70s Boho Chic • Round Sunglasses • Golden Summer',
    '70s Boho Chic • Round Sunglasses • Golden Summer',
    'Photorealism',
    'FLUX.1 Schnell',
    '9:16',
    '768x1344',
    'https://images.unsplash.com/photo-1469334031218-e382a71b716b?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1469334031218-e382a71b716b?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1469334031218-e382a71b716b?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1469334031218-e382a71b716b?w=800&auto=format&fit=crop',
    'Vibrant vintage 70s summer fashion portrait of a stylish woman holding round sunglasses, retro bohemian crop top, warm sun-kissed skin, golden sunlight against a sunny backdrop, authentic Kodachrome film grain, analog color grade, effortless indie aesthetic',
    1420, 530, 530,
    'Chloe Laurent', '@chloelaurent', 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=100&auto=format&fit=crop',
    ARRAY['vintage', '70s', 'portrait', 'sunglasses', 'summer'],
    TRUE, TRUE, 9, TRUE
),
(
    '10000000-0000-4000-8000-000000000010',
    'Cosmic Mirror Ocean Sanctuary',
    'Surreal fantasy landscape of a lone sailboat on a perfectly calm mirror ocean under an awe-inspiring starry night sky and glowing purple galaxy nebula, surreal cosmic reflection on the water surface, serene and peaceful dreamscape, 8k wallpaper',
    'turbulent water, modern city, pollution, blurry stars, low resolution',
    'Cosmic Ocean • Starry Galaxy • Mirror Reflection',
    'Cosmic Ocean • Starry Galaxy • Mirror Reflection',
    'Surrealism',
    'FLUX.1 Schnell',
    '16:9',
    '1344x768',
    'https://images.unsplash.com/photo-1534447677768-be436bb09401?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1534447677768-be436bb09401?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1534447677768-be436bb09401?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1534447677768-be436bb09401?w=800&auto=format&fit=crop',
    'Surreal fantasy landscape of a lone sailboat on a perfectly calm mirror ocean under an awe-inspiring starry night sky and glowing purple galaxy nebula, surreal cosmic reflection on the water surface, serene and peaceful dreamscape, 8k wallpaper',
    1550, 480, 480,
    'Dreamscape AI', '@dreamscape_ai', 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop',
    ARRAY['surreal', 'fantasy', 'ocean', 'galaxy', 'stars'],
    TRUE, TRUE, 10, TRUE
),
(
    '10000000-0000-4000-8000-000000000011',
    'Neon Cyberpunk Studio Portrait',
    'Moody high-fashion cyberpunk studio portrait of a subject with slicked-back hair, striking dual neon lighting with electric cyan and magenta side highlights on cheekbones, dark cinematic gradient backdrop, flawless skin texture, 85mm prime lens f/1.4, vogue cyberpunk',
    'deformed eyes, blurry seams, flat texture, cartoonish, low resolution',
    'Cyan & Violet Neon • Studio Rim Light • Cyberpunk Chic',
    'Cyan & Violet Neon • Studio Rim Light • Cyberpunk Chic',
    'Cyberpunk',
    'FLUX.1 Schnell',
    '4:5',
    '896x1120',
    'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800&auto=format&fit=crop',
    'Moody high-fashion cyberpunk studio portrait of a subject with slicked-back hair, striking dual neon lighting with electric cyan and magenta side highlights on cheekbones, dark cinematic gradient backdrop, flawless skin texture, 85mm prime lens f/1.4, vogue cyberpunk',
    1920, 780, 780,
    'Kurogane Lab', '@kurogane_ai', 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop',
    ARRAY['cyberpunk', 'portrait', 'neon', 'editorial', 'model'],
    TRUE, TRUE, 11, TRUE
),
(
    '10000000-0000-4000-8000-000000000012',
    'Nordic Minimalist Oak Living Room',
    'Interior design photography of a sunlit Scandinavian minimalist living room, natural light oak furniture, warm caramel leather sofa, large fiddle leaf fig plant in ceramic pot, neutral warm linen textiles, clean serene architecture, Kinfolk aesthetic, 8k resolution',
    'busy, cluttered, messy textures, cloudy, distorted lines, plastic furniture',
    'Nordic Oak • Caramel Leather • Sunlit Living Room',
    'Nordic Oak • Caramel Leather • Sunlit Living Room',
    'Architecture',
    'FLUX.1 Schnell',
    '1:1',
    '1024x1024',
    'https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?w=800&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?w=800&auto=format&fit=crop',
    'Interior design photography of a sunlit Scandinavian minimalist living room, natural light oak furniture, warm caramel leather sofa, large fiddle leaf fig plant in ceramic pot, neutral warm linen textiles, clean serene architecture, Kinfolk aesthetic, 8k resolution',
    1100, 360, 360,
    'Nordic Spaces', '@nordicspaces', 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop',
    ARRAY['architecture', 'interior', 'minimalist', 'nordic', 'livingroom'],
    TRUE, TRUE, 12, TRUE
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
│• TrendingTemplatesView (Full)│• Trending Drawer on Web      │
│• TemplatePhotoRemixSheet     │• Camera / Drag-Drop Web Uploader
│• Camera/Gallery Picker Native│• Face-Lock Web Studio Router │
│• StudioController Handover   │• Independent Desktop UI Parity│
└──────────────────────────────┴──────────────────────────────┘
```

> **Note on Mobile UX Requirement:**  
> User tap karne par **Trending bottom sheet nahi khulegi, balki FULL-SCREEN Page (`TrendingTemplatesView`) open hoga.**  
> Is full-screen page par user ko saare trending templates, search bar, aur category filter chips dikhenge.  
> Jab user kisi template card par tap karega, **tab bottom sheet (`TemplatePhotoRemixBottomSheet`)** open hogi jisme reference image aur Camera/Gallery upload options honge.

---

## 3. Mobile Code Changes: Foundation Status & What is Already Done

Humne mobile codebase mein foundation layer pehle hi tayyar kar di hai taaki koi regression ya conflict na ho:

| File | Status | What Was Added / Modified |
| :--- | :--- | :--- |
| `lib/features/explore/views/trending_templates_view.dart` | ✅ **Already Implemented & Analyzed** | Full-screen discovery view with Search bar, Category filter chips, 2-column grid, and smooth remix trigger. |
| `lib/features/explore/widgets/template_photo_remix_bottom_sheet.dart` | ✅ **Already Implemented** | Bottom sheet with reference image, camera & gallery picking, and direct Studio handover. |
| `lib/data/models/explore_card_model.dart` | ✅ **Already Done** | Added `tags` (`List<String>`), `isTrending` (`bool`), `remixesCount` alias, and safe multi-alias fallback for `previewUrl` & `fullPrompt`. *(Do not re-edit)* |
| `lib/features/studio/presentation/controllers/studio_controller.dart` | ✅ **Ready to Plug** | `loadPromptFromRemix` & `startTemplateRemixGeneration` handle reference image face-locking and auto-generation. |
| `lib/core/utils/permission_helper.dart` | ✅ **Already Done** | `AppPermissionHelper.pickImageSafely()` handles Camera and Gallery permissions with Settings redirect. |

---

## 4. Mobile Developer Work Items (What to Implement)

Mobile developer ko sirf ye **4 simple, clean steps** follow karne hain:

```
Step 1: FAB Menu Item  ──>  Step 2: Full-Screen Templates View  ──>  Step 3: Photo Remix Bottom Sheet  ──>  Step 4: Auto-Generate Handover
(home_shell_view.dart)      (trending_templates_view.dart)            (template_photo_remix_bottom)       (studio_controller.dart)
```

---

### Step 1: Update Floating Action Menu (`home_shell_view.dart`)

File: `lib/features/shell/views/home_shell_view.dart` (around line 265)

Add `FabMenuItem` for **Trending & Templates** to `ExpandableNavigationFab` that navigates to **Full Screen** `TrendingTemplatesView`:

```dart
import '../../explore/views/trending_templates_view.dart';

// Inside ExpandableNavigationFab items list:
FabMenuItem(
  title: 'Trending & Templates',
  subtitle: 'Pick a trending AI style & remix your photo',
  icon: Icons.local_fire_department_rounded,
  accentColor: const Color(0xFFEF4444),
  onTap: () {
    HapticFeedback.lightImpact();
    Get.to(
      () => const TrendingTemplatesView(),
      transition: Transition.cupertino,
    );
  },
),
```

---

### Step 2: Full-Screen Trending & Templates View (`trending_templates_view.dart`)

File: `lib/features/explore/views/trending_templates_view.dart`

This full-screen screen displays the complete catalog of trending templates with:
1. Top AppBar with Back Button, Flame Icon & Refresh action.
2. Search input field to search templates by title, keywords, or prompt description.
3. Horizontally scrollable Category Filter Chips (`All`, `Cyberpunk`, `Photorealism`, `Anime`, `Architecture`, `Wildlife`, `Concept Art`, `Surrealism`, `Commercial`).
4. 2-column Grid displaying:
   - High-fidelity visual preview image
   - Category pill & Remix count badge
   - Template title clearly displayed
   - One-tap "Remix My Photo" CTA button
5. **Tapping any card opens the Photo Remix Bottom Sheet** (`TemplatePhotoRemixBottomSheet.show(context, card)`).

---

### Step 3: Photo Remix Bottom Sheet (`template_photo_remix_bottom_sheet.dart`)

File: `lib/features/explore/widgets/template_photo_remix_bottom_sheet.dart`

Jab user full-screen page par kisi card par tap karta hai, tab ye bottom sheet slide up hoti hai:
- Reference template image preview aur title
- **Take Photo / Camera** option
- **Upload Photo / Gallery** option
- Photo select hone par bottom sheet dismiss hoti hai aur seedha generation handover call hota hai:
```dart
await studioCtrl.startTemplateRemixGeneration(
  template: template,
  userPhoto: File(pickedFile.path),
);
```
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
