# MeiGen Creator Studio — Ecosystem Master Blueprint
## Enterprise Architecture & Production Specification: Flutter Mobile, Next.js 15 Web, FastAPI & Supabase

**Document Reference:** MEIGEN-CREATOR-STUDIO-PRODUCTION-BLUEPRINT-V3  
**Target Platforms:** Flutter Mobile (iOS 15+, Android SDK 21–36), Next.js 15 Web Platform (`meigen.ai`), FastAPI Gateway (Python 3.11)  
**Core Innovations:** Pay-to-Download Gating, Marketplace Prompt Royalties, Dynamic Range-Bound Metering, Server-Side AES-256 Prompt DRM  
**Compute Infrastructure:** Google Colab T4 / RunPod Serverless GPU + Direct Serverless Gateways (Gemini Flash, OpenAI, Fal.ai) + Pollinations.ai Fallback  
**Database, Auth & Realtime:** Supabase (PostgreSQL 15+, Row Level Security, pgvector, Supabase Auth SSO, Realtime WebSockets, S3-Compatible Storage)  
**Author:** AI Studio & MeiGen Architecture Engineering Team  
**Date:** September 10, 2026  
**Status:** Approved for Implementation & Executive Sign-off  

---

## 1. Executive Summary & The Creator Economy Flywheel

**MeiGen Creator Studio** is a commercial-grade generative AI creative ecosystem designed to overcome the critical economic and intellectual property shortcomings of traditional generative tools:

### The Industry Challenge:
1. **Upfront Paywalls:** Demanding payment before generation causes an **85%+ drop-off** in user acquisition.
2. **Zero Creator Protection:** Popular prompts are easily scraped or copied from public feeds, leaving prompt engineers unrewarded.

### The Creator Flywheel Architecture:
1. **Creator Workflow:** Creators generate visual artwork in the Studio for free, saved automatically to their private in-app Cloud Library in Supabase. They publish their master prompt setup to the Explore feed.
2. **Consumer Workflow:** Browsing users discover trending visuals in the feed, view aesthetic keywords and variable chips, and pay a range-bound remix fee.
3. **Secure Execution:** The backend decrypts the secret prompt in server memory, injects user customizations, and runs inference directly on serverless GPUs without client-side leakage.
4. **Passive Royalties:** The original prompt author receives a royalty cut (e.g., 40%) credited to their creator wallet, funded strictly via purchased credits to prevent fraud.

### The 4 Core Architectural Pillars:
1. **Freemium Cloud Library vs. Pay-to-Download Gating:** Users experiment, create, and maintain an unlimited visual library in the cloud for free. Exporting unwatermarked, lossless 4K master files to local device storage requires a flat unlock fee of **2 Credits ($0.20)**. Re-downloads of already unlocked images are **100% free (idempotent)**.
2. **Creator Marketplace with Anti-Sybil Royalty Sharing:** Creators publish their prompt setups to the Explore feed. Whenever another user remixes the prompt, the platform automatically splits revenue with the author. Royalties are strictly funded from *purchased credits* to eliminate fake-account bonus farming.
3. **Dynamic Token Complexity Analyzer & Uniform Range Metering:** Incoming prompts are evaluated for compute complexity (token count, aspect ratio, model tier, sampling steps) and billed dynamically within a guaranteed, transparent **uniform range (e.g., 1–3 credits)** using explicit `round_half_up` rounding.
4. **Intellectual Property Protection & Server-Side AES-256 DRM:** Master prompt recipes are encrypted with AES-256-GCM. Browsing users see an obfuscated aesthetic summary; the server decrypts and executes the raw prompt directly on the GPU without ever exposing it to client-side network inspectors.

---

## 2. Core Architectural Deep-Dives

### 2.1 Deep-Dive 1: Freemium Cloud Library & Pay-to-Download Gating (Rule 1)
* **The Problem:** Upfront billing creates immense friction. Pure free models bleed server compute costs.
* **Tier 1: Cloud Canvas & In-App Library (Free):**
  * Outputs are stored in Supabase Storage under `previews/{userId}/{jobId}_preview.webp` (optimized 1024x1024 WebP preview with a subtle dynamic watermark).
  * Users can organize creations into personal folders and view them indefinitely inside the app.
  * Direct saving to device gallery is disabled in Tier 1.
* **Tier 2: Lossless 4K Master Export License (Paywall Gate):**
  * Tapping "Download Full HD (4K)" opens the licensing paywall modal.
  * Spends flat **2 Credits ($0.20)**.
  * Upon atomic payment verification, the backend generates a Supabase Storage Signed URL with a **15-minute (900s) TTL**, providing a robust transfer window for 20MB files over cellular networks.
  * **Idempotent Download Guarantee:** If an unlocked image is re-downloaded later, backend verifies `job.is_download_unlocked == True` and generates a new signed URL for **$0 (free)**.

### 2.2 Deep-Dive 2: Creator Marketplace & Anti-Sybil Royalties (Rule 2)
* **The Marketplace Lifecycle:**
  1. Creator toggles "Publish to Marketplace" on a library creation.
  2. Server strips EXIF metadata, generates public aesthetic keywords, and encrypts the master recipe with AES-256.
  3. Community members discover the card in Explore and tap "Use as Prompt" or "Use as Ref".
  4. On remix execution, an atomic PostgreSQL transaction deducts the remix fee from the buyer and credits the author's earned wallet.
* **Anti-Sybil Protection:**
  * Royalties are credited ONLY if payment is drawn from `purchased_balance`. If a buyer spends free promotional signup credits (`free_daily_balance`), the compute runs, but creator royalty is $0.00. This permanently eliminates sockpuppet cash-farming attacks.
* **Creator Wallet & Payouts:**
  * Earned credits accrue in `wallets.earned_royalty_balance`.
  * Redeemable for Pro generations or cash withdrawals once reaching the **$25.00 minimum threshold** (via Stripe Connect / PayPal Payouts).

### 2.3 Deep-Dive 3: Dynamic Token Complexity Analyzer & Range Metering (Rule 3)
* **Compute Complexity Formula:**
  `Raw Score = Model Base + Word Count Extra + Resolution Extra + Steps Extra + Magic Expander Extra`
  * Model Base: Basic (Flux) = 1.0 Cr, Standard (SDXL) = 3.0 Cr, Pro = 8.0 Cr, Ultra = 15.0 Cr.
  * Word Count: <=30 words = +0; 31-80 words = +1.0; 81+ words = +2.0.
  * Resolution: Square (1:1) = +0; Widescreen/Story (16:9, 9:16) = +0.5; 4K Upscale = +2.0.
  * Sampling Steps: <=20 steps = +0; 21-40 steps = +0.5; Deep passes = +1.0.
  * Magic Expander: Active = +0.5.
* **Guaranteed Uniform Range Guardrails:**
  * `Final Charge = Clamp( RoundHalfUp(Raw Score), Min Range, Max Range )`
  * Basic Tier (Flux): Guaranteed **1 to 3 Credits**.
  * Standard Tier (SDXL): Guaranteed **3 to 6 Credits**.
  * Pro Studio Tier: Guaranteed **8 to 15 Credits**.
  * Ultra Studio: Guaranteed **15 to 22 Credits**.
* **Upfront Pre-Flight UI:**
  * Sticky studio dock displays real-time price: `Generate ✨ 4` with dynamic breakdown: `Tokens: 42 • 16:9 • Standard Range [3-6]`.

### 2.4 Deep-Dive 4: Server-Side AES-256 Prompt DRM (Rule 4)
* **Vulnerability:** On Midjourney, Civitai, or web apps, anyone can inspect network payloads, copy raw prompts, and steal creator intellectual property.
* **MeiGen DRM Pipeline:**
  1. Creator submits master prompt: `"hyperrealistic 8k octane render of cyberpunk ronin, volumetric rim light, kodak portra 400, 85mm f/1.2"`.
  2. Serverless backend generates a public masked summary: `"Cyberpunk Ronin • 85mm Lens • [Secret Formula Protected]"`.
  3. Server encrypts the master prompt with AES-256-GCM using an envelope key stored in Cloud Secret Manager.
  4. Ciphertext is stored in `explore_prompts.prompt_cipher`.
  5. The raw prompt is **never sent to any client**.
  6. On remix execution, the user sends dynamic variable overrides (`{"color": "emerald"}`). The server decrypts the master cipher in memory, merges variables, and streams directly to the GPU worker.
  7. Frontend prevents clipboard copying via native Flutter/Web event interception (`user-select: none`).

---

## 3. MeiGen Feature Parity Matrix (Full Screenshot Integration)

Our platform delivers complete feature parity with MeiGen.ai across all operational modules:

### 1. Explore & Community Prompt Gallery
* **Masonry Grid Layout:** Smooth Pinterest-style feed with infinite scrolling.
* **Semantic Discovery Grid ("More like this"):** Powered by **Supabase pgvector** cosine distance queries (`<=>`), displaying vector-similarity recommendations beneath card details to maximize remix engagement.
* **Category Filters:** Anime, Photorealism, Cyberpunk, 3D Render, Architecture, Product, Logo, Vehicles.
* **Dual-Action Card Drawer:**
  * **`Use as Prompt` (1-Tap Remix):** Injects the prompt recipe and exposed variable chips into the Studio, linking the author for royalty attribution.
  * **`Use as Ref` (1-Tap Image Reference):** Injects the visual asset directly into the Studio's Reference Image slot for IP-Adapter/ControlNet style and pose transfer.
* **Social Engagement:** Likes, Shares, Bookmarks, and Creator Profile views.

### 2. AI Image Creation Studio
* **Consistent Characters & Face Lock:**
  * Users build and save recurring character profiles by uploading **3-angle facial reference photos** (Front, 45° angle, Profile/Side).
  * Profile stored in Supabase under `characters`.
  * Leverages **InstantID (Apache 2.0 Commercial License)** to reconstruct and lock exact facial geometry, bone structure, and identity across unlimited prompts (samurai, cyberpunk, fantasy, professional).
* **Multi-Reference Image Slots (`+ Add reference images`):** Up to 3 reference images for ControlNet (pose, depth, canny) and IP-Adapter (style, lighting).
* **Interactive Studio Bar:**
  * **Batch Count (`- 1/4 +`):** Generate 1, 2, 3, or 4 images concurrently with linear credit calculation.
  * **Seed Lock (`🔒`):** Locks the random generation seed to ensure reproducible visual variations when tweaking minor prompt chips.
  * **Aspect Ratio Selector:** `Auto` (matches uploaded reference image dimensions), `1:1` (Square), `9:16` (Story/Reel), `16:9` (Widescreen), `4:5` (Social Portrait).
  * **Resolution Toggle:** Standard HD, `2K`, and `4K`.
  * **Dynamic Credit Button:** Displays upfront cost (e.g., `Generate ✨ 10`).
* **In-Prompt AI Actions:**
  * **`Enhance` (Magic Expander):** Gemini 1.5 Flash studio prompt expansion (<200ms).
  * **`✨ AI Edit`:** Instructed image modification with human subject lock (`DO NOT CHANGE THE HUMAN SUBJECT. HUMAN SUBJECT — ABSOLUTE LOCK`).
  * **Photo-to-Prompt Scanner:** Gemini Vision interrogator decoding camera gear, lighting, and style from uploaded photos.

### 3. Dedicated AI Video Suite
* **Image-to-Video (I2V) & Text-to-Video (T2V):** Converts still artwork into fluid cinematic videos.
* **LivePortrait Face Motion:** Drives facial animations (Smile, Wink, Talk, Nod) via 12 neural expression presets or driving selfie video.
* **Camera Controls:** Pan Left/Right, Tilt Up/Down, Zoom-in, and 3D Orbit.
* **Duration Selector:** 3-second and 5-second video exports.

### 4. Creative Skills Toolbox
* **AI Background Remover:** 1-tap transparent PNG cutout (U2Net ONNX).
* **Portrait Relighting & Bokeh:** Studio depth-map lighting and DSLR optical blur.
* **4K Lossless Upscaler:** Detail synthesis and super-resolution upscaling.
* **Face Swap & Re-Aging:** InstantID / ReActor under **Apache 2.0 Commercial License**.

### 5. Cloud Library & Creator Dashboard
* Unlimited private cloud storage for all creations in Supabase.
* Custom collections and folders.
* Paginated library synchronization (`GET /api/v1/users/me/library`).
* Download status indicators ("Saved in Cloud" vs "Downloaded to Device").
* Creator analytics: Remix count, earnings balance, and Stripe Connect / PayPal payout button.

---

## 4. Automated Prompt Engineering Pipeline

Everyday users lack expertise in camera optics, lighting schemes, and negative token filters. The platform automates prompt engineering through a **5-Stage Pipeline**:

```
[ User Input / Chips / Reference Photo ]
                    │
                    ▼
[ Stage 1: Template Interpolation ] ── Replaces {variables} with user chip selections
                    │
                    ▼
[ Stage 2: Magic Expander (Gemini 1.5 Flash) ] ── Injects camera gear, lighting & textures (<200ms)
                    │
                    ▼
[ Stage 3: Style Preset Token Injection ] ── Appends style tokens (Anime, Cyberpunk, 8K)
                    │
                    ▼
[ Stage 4: Invisible Negative Prompt Injection ] ── Appends anti-distortion tokens (bad anatomy, extra fingers)
                    │
                    ▼
[ Stage 5: Final GPU Execution String & AES-256 Encryption ] ── Dispatched to Serverless GPU Worker
```

### 4.1 Gemini 1.5 Flash System Directive:
* **System Prompt:**  
  `"You are a master generative AI prompt engineer for Flux and SDXL. Convert the user's short concept into a vivid, photorealistic, studio-grade prompt. Include: (1) Subject details & anatomy, (2) Camera gear (e.g., 85mm f/1.4 lens, Hasselblad), (3) Lighting scheme (e.g., volumetric rim lighting, cinematic shadows), (4) Surface textures & environment, (5) Render fidelity (e.g., 8k, Unreal Engine 5, octane render). Return ONLY the expanded prompt string with no conversational preface or explanation."`
* **Response Latency:** <200ms via Google Cloud Vertex / AI Studio API.

### 4.2 Concrete Transformation Example:
* **Raw User Input:** `"samurai girl in neon city"`
* **Smart Variable Chips Applied:** `Character: Female Ronin | Clothing: Cyberpunk Kimono | Lighting: Neon Rain Reflections`
* **Gemini Magic Output:** `"Cinematic medium portrait of a fierce female ronin samurai wearing an intricate dark carbon-fiber cyberpunk kimono with glowing cyan accents, standing on a wet asphalt street in Neo-Tokyo, reflecting neon magenta billboard lights, light rain drizzle, shot on Hasselblad H6D-100c, 85mm f/1.4 lens, shallow depth of field, volumetric fog, hyper-detailed skin textures, 8k resolution, cinematic color grading."`
* **Server-Injected Negative Prompt:** `"bad anatomy, extra fingers, mutated hands, missing limbs, distorted face, blurry, low resolution, watermark, text, signature, oversaturated, jpeg compression artifacts, duplicate, poorly drawn face."`
* **Execution:** Master recipe is encrypted with AES-256-GCM and stored in Supabase PostgreSQL, while public feeds only display the aesthetic summary.

---

## 5. Financial Model & Unit Economics (98%+ Margins)

* **Exchange Rate:** 10 Credits = $1.00 USD (**1 Credit = $0.10 USD / ~₹8.5 INR**).
* **Credit Packs:** Starter ($1.99 for 25 Cr) • Creator ($4.99 for 70 Cr) • Pro Studio ($14.99 for 250 Cr).
* **Payout Threshold:** Minimum withdrawal is **$25.00** (250 credits) via Stripe Connect / PayPal.
* **Cost vs. Revenue Breakdown (Factoring Compute & Storage Egress):**

| Action | Credits Charged | User Pays | Cloud Cost | Gross Profit | Net Margin (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Basic Image (Flux)** | 2 Credits | $0.200 | $0.0020 | **$0.1980** | **99.0%** |
| **Standard HD (SDXL)** | 4 Credits | $0.400 | $0.0050 | **$0.3950** | **98.7%** |
| **Community Remix\*** | 5 Credits | $0.500 | $0.0050 | **$0.2950** | **59.0% Net\*** |
| **Download 4K Master** | 2 Credits | $0.200 | $0.0025 (Egress) | **$0.1975** | **98.7%** |
| **LivePortrait Video** | 10 Credits | $1.000 | $0.0150 | **$0.9850** | **98.5%** |

*\*Assumes 40% creator royalty ($0.20 paid to creator, $0.30 retained by platform, leaving 59% net margin after compute cost). Re-downloading previously unlocked assets costs $0 (idempotent).*

---

## 6. Creator Royalty Policy: 4 Proposed Models

The royalty split is dynamically configurable via Supabase `app_settings` / FastAPI configuration without requiring app updates:

1. **Model 1: Tiered Gamified Split (Recommended)**
   * Bronze (< 100 remixes): **20% Creator / 80% Platform**
   * Silver (100–500 remixes): **30% Creator / 70% Platform**
   * Gold (500–2,000 remixes): **40% Creator / 60% Platform**
   * Diamond (> 2,000 remixes): **50% Creator / 50% Platform**
   * *Strategic Value:* Motivates creators to share their links externally. Platform keeps an **80% margin on early-tier creators**.
2. **Model 2: Flat Configurable Split (Baseline Proposal)**
   * A single uniform percentage (e.g., 30%, 40%, or 50%) applied platform-wide. Simple to communicate.
3. **Model 3: Fixed Credit Bounty (Compute-Safe)**
   * Flat 1 or 2 Credits paid to creator per remix regardless of model complexity. Insulates platform margins from GPU price shifts.
4. **Model 4: Creator Markup (Open Marketplace)**
   * Creators set their own extra markup (1–5 credits) over base cost; platform takes a 20% commission on the markup.

---

## 7. System Architecture & Technology Division of Labor

```
[ Flutter Mobile App ]               [ Next.js 15 Web Platform ]
(iOS 15+, Android SDK 21–36)         (Desktop Studio & Marketplace SSR)
          │                                        │
          └───────────────────┬────────────────────┘
                              │ HTTPS / WSS
                              ▼
                 [ FastAPI Gateway (Python 3.11) ]
                              │
         ┌────────────────────┴────────────────────┐
         ▼                                         ▼
[ Supabase Cloud Platform ]             [ Asynchronous Task Queue ]
• PostgreSQL 15+ (ACID & RLS)           • Redis / Celery / Cloud Tasks
• Supabase Auth (SSO & JWTs)                       │
• Supabase Realtime (WebSockets)                   ▼
• Supabase Storage (S3-Compatible)      [ Serverless GPU Workers ]
• pgvector (Semantic Discovery)         • RunPod / Modal / T4 Workers
                                        • InstantID (Apache 2.0)
                                        • Flux, SDXL, LivePortrait
                                        • Pollinations.ai Fallback
```

### Division of Responsibility:
* **Flutter Mobile App:**
  - Responsive ScreenUtil architecture (`.w`, `.h`, `.sp`) with zero RenderFlex overflow.
  - Native DRM: Android `FLAG_SECURE` and iOS screen capture detection.
  - Supabase Realtime client: streams completed job status in <50ms.
* **Next.js 15 Web Platform:**
  - High-performance desktop creation studio and public prompt marketplace.
  - Server-Side Rendering (SSR) for prompt discovery and search engine optimization (SEO).
  - Canvas-based DRM protection and right-click interceptors.
* **FastAPI Gateway (Python 3.11):**
  - Non-blocking authentication verification using Supabase JWT tokens (`def get_current_user`).
  - Stripe webhook handler (`POST /api/v1/wallet/stripe-webhook`) for asynchronous credit pack fulfillment.
  - Paginated user library API (`GET /api/v1/users/me/library?page=1&limit=20`).
  - Complexity Tokenizer & Dynamic Price Clamping (`round_half_up`).
  - Gemini 1.5 Flash Magic Prompt Expansion (<200ms).
  - AES-256-GCM Prompt Envelope Encryption / Decryption.
  - Automated EXIF Metadata Stripping (prevents prompt leaks).
  - Supabase Storage Signed URL generator with **15-minute (900s) TTL** for reliable mobile downloads.
* **Supabase (PostgreSQL Database, Auth, Realtime & Storage):**
  - **Supabase Auth:** Google, Apple, Email, and Anonymous SSO with JWTs.
  - **PostgreSQL Database:** ACID relational transactions with Row-Level Locking (`SELECT ... FOR UPDATE`) and Row Level Security (RLS) policies.
  - **`pgvector` Extension:** Built-in vector similarity search powering the **"More like this"** discovery grid.
  - **Supabase Realtime:** WebSocket CDC (Change Data Capture) streaming job completion to Flutter and Next.js in **<50ms** without client polling.
  - **Supabase Storage:** Two-tier S3-compatible buckets (`previews` CDN bucket for WebP; `masters` private bucket for 4K PNGs).
* **Asynchronous Queue:**
  - Fast HTTP 202 ACK on generation requests. Background GPU workers process jobs asynchronously; client UI remains completely non-blocking.

---

## 8. Relational Database Schemas (Supabase PostgreSQL + pgvector)

### 8.1 Table: `public.wallets` (Dual-Balance Ledger)
```sql
CREATE TABLE public.wallets (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    purchased_balance NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (purchased_balance >= 0),
    earned_royalty_balance NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (earned_royalty_balance >= 0),
    free_daily_balance NUMERIC(10, 2) NOT NULL DEFAULT 5.00 CHECK (free_daily_balance >= 0),
    total_generations INT NOT NULL DEFAULT 0,
    total_royalties_earned NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Row Level Security (RLS)
ALTER TABLE public.wallets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own wallet" ON public.wallets
    FOR SELECT USING (auth.uid() = user_id);
```

### 8.2 Table: `public.characters` (Consistent Character Identity Profile)
```sql
CREATE TABLE public.characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    gender TEXT,
    reference_photo_urls TEXT[] NOT NULL,
    face_embedding vector(512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS: Only owner can view and manage their character profiles
ALTER TABLE public.characters ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own characters" ON public.characters
    FOR ALL USING (auth.uid() = user_id);
```

### 8.3 Table: `public.explore_prompts` (Marketplace Prompt Catalog with pgvector)
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE public.explore_prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    preview_url TEXT NOT NULL,
    master_url TEXT NOT NULL,
    category TEXT NOT NULL,
    masked_prompt_summary TEXT NOT NULL,
    prompt_cipher TEXT NOT NULL,
    cipher_iv TEXT NOT NULL,
    prompt_template TEXT NOT NULL,
    template_variables JSONB NOT NULL DEFAULT '[]'::jsonb,
    model_used TEXT NOT NULL DEFAULT 'flux_schnell',
    aspect_ratio TEXT NOT NULL DEFAULT '9:16',
    base_remix_fee NUMERIC(10, 2) NOT NULL DEFAULT 4.00,
    author_royalty_cut NUMERIC(10, 2) NOT NULL DEFAULT 1.60,
    total_remixes INT NOT NULL DEFAULT 0,
    likes_count INT NOT NULL DEFAULT 0,
    prompt_embedding vector(768), -- For "More like this" semantic search
    is_marketplace_public BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for semantic discovery ("More like this")
CREATE INDEX idx_explore_prompts_vector ON public.explore_prompts
USING ivfflat (prompt_embedding vector_cosine_ops) WITH (lists = 100);

-- RLS: Anyone can view public prompts, authors can update own
ALTER TABLE public.explore_prompts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public prompts viewable by all" ON public.explore_prompts
    FOR SELECT USING (is_marketplace_public = TRUE);
```

### 8.4 Table: `public.jobs` (Generation Job with Download Licensing State)
```sql
CREATE TABLE public.jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    type TEXT NOT NULL DEFAULT 'IMAGE_GEN',
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    model_used TEXT NOT NULL,
    tokens_analyzed INT NOT NULL DEFAULT 0,
    credits_deducted NUMERIC(10, 2) NOT NULL,
    preview_image_url TEXT,
    master_image_url TEXT,
    is_download_unlocked BOOLEAN NOT NULL DEFAULT FALSE,
    download_unlocked_at TIMESTAMPTZ,
    download_cost NUMERIC(10, 2) NOT NULL DEFAULT 2.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS: Users can only see own jobs
ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own jobs" ON public.jobs
    FOR SELECT USING (auth.uid() = user_id);
```

### 8.5 Table: `public.royalty_transactions` (Financial Audit Trail)
```sql
CREATE TABLE public.royalty_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    buyer_user_id UUID NOT NULL REFERENCES auth.users(id),
    creator_user_id UUID NOT NULL REFERENCES auth.users(id),
    prompt_id UUID NOT NULL REFERENCES public.explore_prompts(id),
    total_fee_charged NUMERIC(10, 2) NOT NULL,
    creator_royalty_credited NUMERIC(10, 2) NOT NULL,
    platform_fee_retained NUMERIC(10, 2) NOT NULL,
    funded_from TEXT NOT NULL DEFAULT 'purchased_balance',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS: Service role only writes; users view where they are buyer or creator
ALTER TABLE public.royalty_transactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view relevant royalty logs" ON public.royalty_transactions
    FOR SELECT USING (auth.uid() = buyer_user_id OR auth.uid() = creator_user_id);
```

---

## 9. Security Hardening & Exploit Mitigation Matrix

| Vulnerability / Attack Vector | Threat Scenario | Production Defense |
| :--- | :--- | :--- |
| **1. Sybil Royalty Farming** | Scripting 500 fake accounts using free signup credits to remix an author's prompt and extract cash. | **Purchased-Credit Gating**. Royalties are strictly credited only if payment is deducted from `purchased_balance`. Free/promo credits yield 0 cash royalty. |
| **2. Double-Spend Race** | Rapid concurrent taps attempting to spend 3 credits on 10 parallel jobs. | **PostgreSQL ACID Lock (`SELECT ... FOR UPDATE`) + Redis Distributed Lock**. Concurrent calls queue or reject. |
| **3. Re-Download Overcharge** | Users getting recharged 2 credits when re-downloading an already unlocked image after link expiry. | **Idempotent Unlock Check**. Backend checks `job.is_download_unlocked`; if True, skips deduction and serves signed URL for free. |
| **4. Expired Mobile Downloads** | 60-second signed URL expiring mid-transfer on slow 3G/4G connections for 20MB files. | **15-Minute (900s) Signed URL TTL**. Sufficient window for large mobile transfers via Supabase Storage without exposing persistent links. |
| **5. Commercial Licensing Risk** | Using non-commercial research models (e.g. InsightFace) in a commercial SaaS app. | **Permissive Licensing**. Using **InstantID (Apache 2.0)** and **ReActor / CodeFormer** for 100% legal commercial compliance. |
| **6. EXIF Metadata Leak** | Diffusion models embedding raw prompts inside image metadata headers. | **Automated EXIF Purge**. Backend strips all metadata (`exif=b""`) before writing public previews. |
| **7. Platform DRM Security** | Preventing screenshots and prompt theft across platforms. | **Native Mobile DRM** (`FLAG_SECURE` on Android, `UIScreen.capturedDidChangeNotification` on iOS) + Canvas DOM obfuscation on Next.js Web. |

---

## 10. Technical Challenges, System Limitations & Mitigations

| Challenge / Limitation | Impact Description | Engineering Mitigation |
| :--- | :--- | :--- |
| **1. GPU Cold Starts (Serverless Latency)** | Spinning up a new serverless GPU worker from 0 takes 15–25s to load weights (Flux/SDXL 12–24GB), causing wait spikes during sudden traffic surges. | • Keep 1 warm standby worker during peak daytime hours (min-instances=1); • Cache model weights on fast NVMe / RunPod Network Volumes; • Instant failover to Pollinations / hosted fallback if cold start exceeds 5s. |
| **2. Large 4K File Downloads on Mobile Networks** | Uncompressed 4K master files are ~15MB–25MB. Users on spotty 3G/4G or tier-2 networks risk connection timeouts. | • Extended Supabase Storage Signed URL TTL to 15 minutes (900s); • Implemented Flutter chunked background download manager; • Free idempotent re-downloads if network drops mid-transfer. |
| **3. Web Browser DRM Limitations vs. Native Mobile** | Native mobile enforces OS-level `FLAG_SECURE` (Android) and `UIScreen` capture blocking (iOS). Web browsers cannot 100% block external phone cameras or OS-level screen capture tools. | • Master prompt ciphers are strictly kept server-side (never delivered to web clients); • Next.js web clients use Canvas DOM rendering and disabled right-click context menus; • Public feeds only expose high-level chips, preserving master recipes. |
| **4. GPU Queue Concurrency Caps & Cost Protection** | A viral prompt could trigger thousands of concurrent remix calls, risking runaway serverless compute bills. | • Redis Token-Bucket rate limiting (max 5 active jobs per free user); • Global auto-scale cap (max 20 concurrent GPU workers); • Asynchronous HTTP 202 queue buffering to prevent server crash. |
| **5. Third-Party LLM & API Quota Bottlenecks** | Google Gemini 1.5 Flash API could hit rate limit caps (RPM/TPM) during peak platform marketing campaigns. | • In-memory Redis caching for identical prompt expansion requests (TTL 1hr); • Pre-computed style tokens; • Automatic graceful fallback to local template interpolator if LLM API is unavailable. |
| **6. Content Moderation & NSFW Filtration** | Users attempting to input prompt jailbreaks or generate harmful, copyrighted, or NSFW outputs. | • Multi-tier moderation gate: (1) Gemini Safety Settings on Magic Prompt expander, (2) Server-side negative keyword blocklist, and (3) Safety-checker post-processing on GPU inference before saving outputs. |

---

## 11. Phased Implementation Roadmap (8 Weeks / 4 Sprints)

| Sprint | Focus Area | Key Deliverables |
| :--- | :--- | :--- |
| **Sprint 1 (Weeks 1–2)** | Core DRM, Supabase & Paywall | • Supabase PostgreSQL Schema, RLS & Storage Buckets; • In-App Cloud Library; • 2-Credit Idempotent Download Paywall; • 15-Minute Supabase Signed URLs; • Stripe Webhook (`POST /api/v1/wallet/stripe-webhook`); • Mobile `FLAG_SECURE` copy protection |
| **Sprint 2 (Weeks 3–4)** | AI Engine & Pricing | • Complexity Tokenizer & Range Clamping algorithm (`round_half_up`); • Gemini 1.5 Flash Magic Expander; • Self-hosted T4 GPU worker with Pollinations fallback; • Next.js 15 Web Studio Scaffold |
| **Sprint 3 (Weeks 5–6)** | Marketplace & Royalties | • Server-Side AES-256 Prompt DRM; • Anti-Sybil Royalty Transaction Ledger (`purchased_balance` gating); • Explore Masonry Grid & 1-Tap Remix drawer; • Supabase `pgvector` semantic discovery |
| **Sprint 4 (Weeks 7–8)** | Video Suite & Hardening | • LivePortrait neural face motion pipeline; • InstantID face swap pipeline (Apache 2.0); • Next.js 15 SSR Production Build; • Automated CI/CD pipelines & production launch |

---

## 12. Executive Sign-Off & Approvals

To initiate Sprint 1 implementation, alignment is confirmed on:
1. **Tech Stack Selection:** Implementation on **Flutter Mobile (iOS/Android)**, **Next.js 15 Web Platform**, **FastAPI (Python)**, and **Supabase (PostgreSQL, Auth, Storage, Realtime, pgvector)**.
2. **Royalty Policy:** Implementation of **Model 1 (Tiered Gamified Split)** as default setting in remote configuration with Anti-Sybil purchased-credit gating.
3. **Download Paywall:** **Flat 2 Credits ($0.20)** for master unwatermarked file downloads, with free idempotent re-downloads.
4. **Licensing Compliance:** Mandatory deployment of **InstantID (Apache 2.0)** and ReActor for commercial viability.
5. **Implementation Kickoff:** Authorization to commence Sprint 1 engineering deliverables.
