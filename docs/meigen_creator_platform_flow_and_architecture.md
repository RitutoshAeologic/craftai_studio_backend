# MeiGen Creator Studio — Production Architecture, System Flow & Executive Summary Blueprint

> **Document Classification:** Enterprise Executive Architecture & System Flow Specification  
> **Document Purpose:** Complete architectural flow, business model, engineering topology, and security mitigation blueprint synthesized into a structured, key-point format for executive review and sign-off.  
> **Target Review Time:** 8–10 minutes (~5–6 pages in MS Word).  
> **Target Tech Stack:** Flutter Mobile (iOS/Android) • Next.js 15 Web Platform • FastAPI Gateway (Python) • Supabase (PostgreSQL, Auth, Storage, Realtime, pgvector) • Redis Task Queue • Serverless GPU Workers.

---

# PART I: PRODUCT & BUSINESS FOUNDATION

## 1. Executive Summary & Value Proposition

MeiGen Creator Studio combines a **high-fidelity AI Image & Video Creation Studio** with a **Curated Prompt Marketplace** (achieving full parity with MeiGen.ai), deployed across **Flutter Mobile** and **Next.js 15 Web Platform**.

### Industry Problems Solved:
1. **Upfront Paywalls:** Demanding payment before generation causes an **85%+ user drop-off**.
2. **Unprotected Creator Work:** Creators invest hours engineering prompts only to have them copied from public feeds without reward.

### The Creator Flywheel Model:
* **Frictionless Creation:** Users generate and curate unlimited images inside their in-app Cloud Library for free.
* **Monetization at Intent (Rule 1):** Exporting unwatermarked, lossless 4K master files to local device storage costs **flat 2 Credits ($0.20)**. Re-downloads are **100% free (idempotent)**.
* **Passive Creator Royalties (Rule 2):** Creators publish encrypted prompts to the Explore feed and earn **royalties on every community remix** (remotely configurable via Supabase).
* **Guaranteed Uniform Pricing (Rule 3):** Compute charges scale dynamically with prompt complexity, but are strictly bounded within transparent **uniform tier brackets (e.g., 1–3 credits)**.
* **Encrypted Prompt DRM (Rule 4):** Prompts are AES-256 encrypted; client UI displays aesthetic abstracts only, and clipboard copying is blocked.

---

## 2. The 4 Core Business Rules

| Rule | Functional Mechanism | Business & Technical Value |
| :--- | :--- | :--- |
| **Rule 1: Pay-to-Download** | In-app creation and cloud library are free. Unlocking high-res 4K files to device gallery requires **2 credits ($0.20)** on first export; subsequent re-downloads are free. | Eliminates user onboarding friction while monetizing high-intent exports without unfair double-charging. |
| **Rule 2: Creator Royalties** | Creators earn royalties whenever community members remix their published prompts. Split is dynamically configurable. Funded strictly via *purchased credits*. | Generates organic user growth; creators actively bring their audience to earn passive income safely. |
| **Rule 3: Range-Bound Dynamic Pricing** | Compute charges adjust by prompt tokens, model, and resolution, but remain strictly locked inside **predefined Min–Max limits**. | Fair compute-based billing without bill shocks or unexpected overcharges. |
| **Rule 4: Encrypted Prompt DRM** | Prompts are AES-256 encrypted on the server; client UI displays aesthetic abstracts only. Direct copy is blocked on mobile and web. | Protects creators' proprietary prompt recipes from plagiarism without misleading claims. |

---

## 3. MeiGen Core Feature Matrix (Full Parity)

| Module | Core Capabilities |
| :--- | :--- |
| **1. Explore & Prompt Gallery** | • Pinterest-style masonry grid feed with semantic **"More like this"** discovery grid powered by **Supabase pgvector**; • Category filters (Anime, Photorealism, Cyberpunk, 3D, Product, Logo); • Sorting: Trending, Most Remixed, Top Rated; • **Dual-Action Card Actions:** **`Use as Prompt`** (1-Tap Remix formula) and **`Use as Ref`** (1-Tap Image Reference injection); • Social engagement: Likes, Shares, Creator Profiles |
| **2. AI Image Creation Studio** | • **Consistent Characters & Face Lock:** Save recurring character profiles with **3-angle facial reference photos** (Front, 45°, Side) using InstantID Apache 2.0; • Multi-reference image slots (`+ Add reference images`); • Interactive Studio Bar: Batch Count (`- 1/4 +`), Seed Lock (`🔒`), Aspect Ratio (`Auto`, 1:1, 9:16, 16:9), Resolution (`2K / 4K`); • Dynamic button: `Generate ✨ {credits}` |
| **3. In-Prompt AI Actions & Expander** | • **`Enhance` (Magic Expander):** Gemini 1.5 Flash studio expansion (<200ms); • **`✨ AI Edit`:** Instructed image modification with Subject Lock (`EDIT THE PROVIDED PHOTO — ABSOLUTE LOCK`); • Photo-to-Prompt vision scanner |
| **4. Dedicated AI Video Suite** | • Image-to-Video (I2V) and Text-to-Video (T2V); • LivePortrait Face Motion (Smile, Wink, Talk, Head Movement via preset animations & user driving video); • Camera controls (Pan, Tilt, Zoom, 3D Orbit); • 3s & 5s durations |
| **5. Creative Skills Toolbox** | • AI Background Remover (Transparent PNG); • Portrait Relighting & Bokeh Blur; • 4K Lossless Upscaler; • Face Swap & Re-Aging (InstantID / ReActor — **Apache 2.0 Commercial License**) |
| **6. Cloud Library & Creator Dashboard** | • Unlimited private cloud storage in Supabase; • Custom collections/folders; • Paginated library sync (`GET /api/v1/users/me/library`); • Download status tracking; • Creator analytics (Remix count, earnings, payout request) |

---

## 4. End-to-End User & Creator Flows

* **Flow A: Free In-App Creation**  
  User enters prompt ➔ Optional 1-tap Magic Expander adds studio tags ➔ Complexity Tokenizer calculates credit cost ➔ Serverless GPU generates image in 2–4s ➔ Saved permanently in user's in-app Cloud Library for free.
* **Flow B: Pay-to-Download Master File (Rule 1)**  
  User opens image in Cloud Library ➔ Taps "Download 4K Master" ➔ 2-Credit Paywall Sheet appears ➔ Wallet deducted via PostgreSQL ACID transaction (`SELECT ... FOR UPDATE`) ➔ Supabase Storage Signed URL generated with **15-Minute (900s) TTL** ➔ Lossless PNG saved to device storage (re-downloads are free).
* **Flow C: Publish Prompt to Marketplace (Rule 2)**  
  User selects generation from library ➔ Toggles "Publish to Explore" ➔ System generates aesthetic summary and encrypts master prompt with AES-256-GCM ➔ Generates `pgvector` embedding ➔ Prompt appears in community feed with creator attribution.
* **Flow D: Community Remix with Server-Side AES-256 DRM (Rule 4)**  
  User browses Explore feed (copying blocked) ➔ Taps "Remix" drawer ➔ Customizes exposed variable chips (`[lighting]`, `[character]`) ➔ Server decrypts cipher in memory and passes directly to GPU ➔ Creator receives royalty credit in wallet (funded strictly via purchased credits).
* **Flow E: Automated Prompt Optimization Engine**  
  Raw 2-word user idea ➔ Gemini 1.5 Flash expands with camera, lens, and lighting tokens ➔ Server appends negative prompt filter (anti-distortion) ➔ Flawless output generated.

---

## 5. Unit Economics & Profit Margin Model

### 5.1 Pricing Structure
* **Standard Exchange Rate:** 10 Credits = $1.00 USD (**1 Credit = $0.10 USD / ~₹8.5 INR**).
* **Credit Packs:** Starter Pack ($1.99 for 25 Cr) • Creator Pack ($4.99 for 70 Cr) • Pro Studio Pack ($14.99 for 250 Cr).
* **Payout Threshold:** Minimum creator withdrawal is **$25.00** (250 credits) via Stripe Connect or PayPal Payouts API.

### 5.2 Compute & Bandwidth Cost vs. Revenue Margin Breakdown

| User Action | Credits Paid | Gross Revenue | Cloud / Compute Cost | Net Profit Margin (%) |
| :--- | :---: | :---: | :---: | :---: |
| **Basic Image (Flux)** | 2 Credits | $0.200 | $0.0020 | **$0.1980 (99.0% Margin)** |
| **Standard HD (SDXL)** | 4 Credits | $0.400 | $0.0050 | **$0.3950 (98.7% Margin)** |
| **Community Remix\*** | 5 Credits | $0.500 | $0.0050 | **$0.2950 (59.0% Net)\*** |
| **Download 4K Master** | 2 Credits | $0.200 | $0.0025 (Egress Bandwidth) | **$0.1975 (98.7% Margin)** |
| **LivePortrait Video** | 10 Credits | $1.000 | $0.0150 | **$0.9850 (98.5% Margin)** |

*\*Assumes 40% creator royalty ($0.20 paid to creator, $0.30 retained by platform, leaving 59% net margin after compute cost). Re-downloads of already unlocked images are idempotent ($0 charge).*

---

# PART II: AI & PRICING ENGINES

## 6. Prompt Engineering & Generation Pipeline (Step-by-Step Architecture)

The platform guarantees studio-quality outputs through an automated **5-Stage Prompt Generation Pipeline**:

### 6.1 The 3 Input Channels (How Prompts Originate)
1. **Channel A: Raw Text + Magic Expander:** User types a brief 2-3 word concept (e.g. *"cyberpunk supercar"*).
2. **Channel B: Smart Template Chips (Remix Mode):** 80% of the prompt is pre-engineered by master creators; users customize dynamic variable dropdown chips (`{character}`, `{clothing}`, `{lighting}`).
3. **Channel C: Vision Interrogation (Photo-to-Prompt):** User uploads an aesthetic reference photo; Gemini 1.5 Flash Vision decodes camera lens, lighting angles, and color palette into a prompt recipe.

### 6.2 The 5-Stage Prompt Assembly Pipeline

```
[ User Input / Chips / Photo ] 
            │
            ▼
[ Stage 1: Template Interpolation ] ── Replaces {variables} with user chip selections
            │
            ▼
[ Stage 2: Magic Expander (Gemini 1.5 Flash) ] ── Injects camera, lens, lighting & textures (<200ms)
            │
            ▼
[ Stage 3: Style Preset Token Injection ] ── Injects style tokens (Anime, Cyberpunk, Photorealism, 3D)
            │
            ▼
[ Stage 4: Invisible Negative Prompt Injection ] ── Appends anti-distortion tokens (deformed, blurry, 6-finger block)
            │
            ▼
[ Stage 5: Final GPU Execution String & AES-256 Encryption ] ── Dispatched to Serverless GPU Worker
```

### 6.3 Gemini 1.5 Flash System Instruction (Expansion Prompt)
When the user taps **🪄 Magic Prompt**, FastAPI invokes Gemini 1.5 Flash with the following system directive:
* **System Prompt:**  
  `"You are a master generative AI prompt engineer for Flux and SDXL. Convert the user's short concept into a vivid, photorealistic, studio-grade prompt. Include: (1) Subject details & anatomy, (2) Camera gear (e.g., 85mm f/1.4 lens, Hasselblad), (3) Lighting scheme (e.g., volumetric rim lighting, cinematic shadows), (4) Surface textures & environment, (5) Render fidelity (e.g., 8k, Unreal Engine 5, octane render). Return ONLY the expanded prompt string with no conversational preface or explanation."`
* **Response Time:** <200ms via Google Cloud Vertex / AI Studio API.

### 6.4 Concrete Real-World Prompt Transformation Example
* **Step 1 — Raw User Input:**  
  `"samurai girl in neon city"`
* **Step 2 — Smart Chips Applied:**  
  `Character: Female Ronin | Clothing: Cyberpunk Kimono | Lighting: Neon Rain Reflections`
* **Step 3 — Gemini Magic Prompt Output:**  
  `"Cinematic medium portrait of a fierce female ronin samurai wearing an intricate dark carbon-fiber cyberpunk kimono with glowing cyan accents, standing on a wet asphalt street in Neo-Tokyo, reflecting neon magenta billboard lights, light rain drizzle, shot on Hasselblad H6D-100c, 85mm f/1.4 lens, shallow depth of field, volumetric fog, hyper-detailed skin textures, 8k resolution, cinematic color grading."`
* **Step 4 — Invisible Negative Prompt (Auto-Injected by Server):**  
  `"bad anatomy, extra fingers, mutated hands, missing limbs, distorted face, blurry, low resolution, watermark, text, signature, oversaturated, jpeg compression artifacts, duplicate, poorly drawn face."`
* **Step 5 — Final GPU Inference Payload:**  
  The positive and negative strings are dispatched to the serverless GPU worker (Flux/SDXL). Simultaneously, the positive recipe is **encrypted with AES-256-GCM** and stored in Supabase PostgreSQL, while public feeds only display the aesthetic summary.

---

## 7. Dynamic Pricing Engine & Uniform Ranges (Rule 3)

### 7.1 Compute Parameters

| Parameter | Metric / Trigger | Credit Impact |
| :--- | :--- | :---: |
| **Model Base Cost** | Basic (Flux) = 1 Cr; Standard (SDXL) = 3 Cr; Pro = 8 Cr; Ultra = 15 Cr | 1.0 to 15.0 Credits |
| **Word Count Tokens** | Short (<=30 words) = +0; Medium (31–80 words) = +1; Long (81+ words) = +2 | +0.0 to +2.0 Credits |
| **Resolution Impact** | Square (1:1) = +0; Widescreen / Story (16:9, 9:16) = +0.5; 4K Upscale = +2.0 | +0.0 to +2.0 Credits |
| **Sampling Steps** | Fast (<=20 steps) = +0; High Quality (21–40 steps) = +0.5; Deep passes = +1.0 | +0.0 to +1.0 Credit |
| **Magic Expander** | Raw text = +0; Magic Expander activated = +0.5 | +0.0 or +0.5 Credit |

### 7.2 Formula & Uniform Range Brackets
* **Compute Formula:** `Raw Score = Model Base + Word Delta + Resolution Delta + Steps Delta + Magic Delta`
* **Guaranteed Billed Credits:** `Final Charge = Clamp( RoundHalfUp(Raw Score), Min Range, Max Range )`

| Tier Category | Minimum Credit Cap | Maximum Credit Cap | Guarantee |
| :--- | :---: | :---: | :--- |
| **Basic Tier (Flux)** | 1 Credit | 3 Credits | Never charges > 3 credits regardless of prompt length. |
| **Standard Tier (SDXL)** | 3 Credits | 6 Credits | Never charges > 6 credits regardless of resolution. |
| **Pro Studio Tier** | 8 Credits | 15 Credits | Fixed bracket for high-end multimodal models. |
| **Download Master File** | 2 Credits | 2 Credits | Flat uniform rate for all exports. |

---

## 8. Creator Royalty Architecture: 4 Proposed Models

> **Implementation Note:** The royalty split is **dynamically configurable** via Supabase `app_settings` / FastAPI configuration without requiring app updates or redeployments.

1. **Model 1: Tiered Gamified Split (Recommended)**
   * Bronze (< 100 remixes): **20% Creator / 80% Platform**
   * Silver (100–500 remixes): **30% Creator / 70% Platform**
   * Gold (500–2,000 remixes): **40% Creator / 60% Platform**
   * Diamond (> 2,000 remixes): **50% Creator / 50% Platform**
   * *Strategic Value:* Gamification motivates creators to self-promote. Platform maintains an **80% margin on early-tier creators**.
2. **Model 2: Flat Configurable Split (Baseline Proposal)**
   * A single uniform percentage (e.g., 30%, 40%, or 50%) applied platform-wide. Simple to understand and audit.
3. **Model 3: Fixed Credit Bounty (Compute-Safe)**
   * Flat 1 or 2 Credits paid to creator per remix regardless of model complexity. Insulates platform margins from GPU price shifts.
4. **Model 4: Creator Markup (Open Marketplace)**
   * Creators choose an extra markup (1–5 credits) over base cost; platform takes a 20% commission on the markup.

---

# PART III: TECHNICAL ARCHITECTURE & DEVOPS

## 9. High-Level Architecture & Technology Division of Labor

```
[ Flutter Mobile App ]          [ Next.js 15 Web Platform ]
(iOS 15+, Android SDK 21–36)    (Desktop Studio & Marketplace SSR)
          │                                   │
          └─────────────────┬─────────────────┘
                            │ HTTPS / WSS
                            ▼
               [ FastAPI Gateway (Python 3.11) ]
                            │
         ┌──────────────────┴──────────────────┐
         ▼                                     ▼
[ Supabase Cloud Platform ]         [ Asynchronous Task Queue ]
• PostgreSQL 15+ (ACID & RLS)       • Redis / Celery / Cloud Tasks
• Supabase Auth (SSO & JWTs)                   │
• Supabase Realtime (WebSockets)               ▼
• Supabase Storage (S3-Compatible)  [ Serverless GPU Workers ]
• pgvector (Semantic Discovery)     • RunPod / Modal / T4 Workers
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
  - WebGL / Canvas studio viewport with interactive controls and responsive sidebar.
  - Canvas-based DRM protection and right-click interceptors.
* **FastAPI Gateway (Python 3.11):**
  - Non-blocking authentication verification using Supabase JWT tokens (`def get_current_user`).
  - Stripe webhook handler (`POST /api/v1/wallet/stripe-webhook`) for asynchronous credit pack fulfillment.
  - Paginated user library API (`GET /api/v1/users/me/library?page=1&limit=20`).
  - Complexity Tokenizer & Dynamic Price Clamping (`round_half_up`).
  - Gemini 1.5 Flash Magic Prompt Expansion (<200ms).
  - AES-256-GCM Prompt Envelope Encryption / Decryption.
  - Automated EXIF Metadata Stripping (prevents prompt leaks).
  - Supabase Storage Signed URL generator with **15-minute (900s) TTL** for reliable mobile downloading.
* **Supabase (PostgreSQL Database, Auth, Realtime & Storage):**
  - **Supabase Auth:** Google, Apple, Email, and Anonymous SSO with JWTs.
  - **PostgreSQL Database:** ACID relational transactions with Row-Level Locking (`SELECT ... FOR UPDATE`) and Row Level Security (RLS) policies.
  - **`pgvector` Extension:** Built-in vector similarity search powering the **"More like this"** discovery grid.
  - **Supabase Realtime:** WebSocket CDC (Change Data Capture) streaming job completion to Flutter and Next.js in **<50ms** without client polling.
  - **Supabase Storage:** Two-tier S3-compatible buckets (`previews` CDN bucket for WebP; `masters` private bucket for 4K PNGs).

---

## 10. Prompt DRM, Encryption & Security Architecture (Rule 4)

1. **Client Obfuscation:** Prompt text selection is disabled (`user-select: none`). Public cards display aesthetic keywords only.
2. **Server-Side AES-256-GCM Encryption:** Prompts are encrypted using an initialization vector (IV) and authentication tag before storage.
3. **Server-Side In-Memory Decryption (Zero-Client-Exposure):** During community remixes, the backend decrypts the prompt directly into memory and forwards it to the GPU; the raw prompt is never exposed to the client or network requests.
4. **Automated EXIF Scrubbing:** Before generating public previews, the server strips all embedded metadata headers (`exif=b""`), ensuring proprietary recipes cannot be recovered from downloaded preview images.

---

## 11. Frontend Architecture: Flutter Mobile & Next.js 15 Web

### 11.1 Flutter Mobile Architecture (`flutter_screenutil`)
1. **Universal Responsive Sizing:**
   * Baseline Design Canvas: **390 × 844 dp** (Standard mobile viewport).
   * Strict scaling rules: Width `.w`, Height `.h`, Radius `.r`, Typography `.sp`.
2. **Defensive Layout Guidelines (Zero-Overflow):**
   * Variable prompt chips wrapped in `Wrap(spacing: 8.w)` (never unconstrained `Row` widgets).
   * All dynamic text wrapped in `Flexible` / `Expanded` with `TextOverflow.ellipsis`.
   * Form canvases enclosed within `SingleChildScrollView` to prevent keyboard resize crashes.
3. **Design System Color Tokens:**
   * Background: Deep Dark `#0B0F19` • Surface: Elevated `#151D2F` • Primary: Neon Cyan `#00F2FE` • Secondary: Electric Blue `#4FACFE` • VIP: Deep Purple `#7F00FF`.

### 11.2 Next.js 15 Web Architecture (App Router & SSR)
1. **App Router with React Server Components (RSC):**
   * Pre-renders marketplace cards on the server for instant page load and high SEO indexability.
   * Client components isolated to interactive studio widgets (canvas preview, sliders, chips).
2. **Supabase SSR Authentication:**
   * Secure session management via `@supabase/ssr` with HTTP-only cookies, eliminating token storage in localStorage.
3. **Web DRM & Anti-Scraping Defenses:**
   * Disabled context menus (`onContextMenu="return false;"`).
   * Canvas DOM rendering for preview assets and CSS selection blocking (`user-select: none;`).

---

## 12. DevOps, Containerization & CI/CD Strategy

1. **Containerization:** Multi-stage Docker build utilizing Python 3.11-slim; non-root user execution (`appuser:10001`); compiled wheels cached.
2. **Serverless Orchestration:** FastAPI gateway deployed to Google Cloud Run / AWS ECS with automatic concurrency autoscaling (min 1, max 100 instances).
3. **CI/CD Pipeline (GitHub Actions):**
   * Lint & Static Analysis: `flake8`, `black`, `mypy`.
   * Automated Unit & Integration Tests: `pytest` with 90%+ branch coverage target.
   * Container Build & Scan: Trivy vulnerability scanner.
   * Staging & Production Deployment: Zero-downtime rolling update via Google Artifact Registry.

---

## 13. System Resilience & Graceful Fallbacks

1. **Circuit Breaker Pattern:** Wrapped around third-party AI APIs; trips after 5 consecutive failures, failing over instantly to fallback providers.
2. **Multi-Engine Fallback Matrix:**
   * Primary Provider: Self-Hosted T4 Worker on RunPod ($0.22/hr).
   * Secondary Provider: Free / Low-cost Pollinations AI Gateway.
   * Tertiary Failover: Hosted SDXL API endpoint.
3. **Dead Letter Queue (DLQ):** Failed generation jobs auto-retry 3 times with exponential backoff before triggering automatic credit refund to user wallet.

---

## 14. Security Hardening & Exploit Mitigation Matrix

| Vulnerability / Attack Vector | Threat Scenario | Production Defense |
| :--- | :--- | :--- |
| **1. Sybil Royalty Farming** | Scripting 500 fake accounts using free signup credits to remix an author's prompt and extract cash. | **Purchased-Credit Gating**. Royalties are strictly credited only if payment is deducted from `purchased_balance`. Free/promo credits yield 0 cash royalty. |
| **2. Double-Spend Race** | Rapid concurrent taps attempting to spend 3 credits on 10 parallel jobs. | **PostgreSQL ACID Lock (`SELECT ... FOR UPDATE`) + Redis Distributed Lock**. Concurrent calls queue or reject safely. |
| **3. Re-Download Overcharge** | Users getting recharged 2 credits when re-downloading an already unlocked image after link expiry. | **Idempotent Unlock Check**. Backend checks `job.is_download_unlocked`; if True, skips deduction and serves signed URL for free. |
| **4. Expired Mobile Downloads** | 60-second signed URL expiring mid-transfer on slow 3G/4G connections for 20MB files. | **15-Minute (900s) Signed URL TTL**. Sufficient window for large mobile transfers via Supabase Storage without exposing persistent links. |
| **5. Commercial Licensing Risk** | Using non-commercial research models (e.g. InsightFace) in a commercial SaaS app. | **Permissive Licensing**. Using **InstantID (Apache 2.0)** and **ReActor / CodeFormer** for 100% legal commercial compliance. |
| **6. EXIF Metadata Leak** | Diffusion models embedding raw prompts inside image metadata headers. | **Automated EXIF Purge**. Backend strips all metadata (`exif=b""`) before writing public previews. |
| **7. Platform DRM Security** | Preventing screenshots and prompt theft across platforms. | **Native Mobile DRM** (`FLAG_SECURE` on Android, `UIScreen.capturedDidChangeNotification` on iOS) + Canvas DOM obfuscation on Next.js Web. |

---

## 15. Technical Challenges, System Limitations & Mitigation Strategies

| Challenge / Limitation | Impact Description | Engineering Mitigation |
| :--- | :--- | :--- |
| **1. GPU Cold Starts (Serverless Latency)** | Spinning up a new serverless GPU worker from 0 takes 15–25s to load weights (Flux/SDXL 12–24GB), causing wait spikes during sudden traffic surges. | • Keep 1 warm standby worker during peak daytime hours (min-instances=1); • Cache model weights on fast NVMe / RunPod Network Volumes; • Instant failover to Pollinations / hosted fallback if cold start exceeds 5s. |
| **2. Large 4K File Downloads on Mobile Networks** | Uncompressed 4K master files are ~15MB–25MB. Users on spotty 3G/4G or tier-2 networks risk connection timeouts. | • Extended Supabase Storage Signed URL TTL to 15 minutes (900s); • Implemented Flutter chunked background download manager; • Free idempotent re-downloads if network drops mid-transfer. |
| **3. Web Browser DRM Limitations vs. Native Mobile** | Native mobile enforces OS-level `FLAG_SECURE` (Android) and `UIScreen` capture blocking (iOS). Web browsers cannot 100% block external phone cameras or OS-level screen capture tools. | • Master prompt ciphers are strictly kept server-side (never delivered to web clients); • Next.js web clients use Canvas DOM rendering and disabled right-click context menus; • Public feeds only expose high-level chips, preserving master recipes. |
| **4. GPU Queue Concurrency Caps & Cost Protection** | A viral prompt could trigger thousands of concurrent remix calls, risking runaway serverless compute bills. | • Redis Token-Bucket rate limiting (max 5 active jobs per free user); • Global auto-scale cap (max 20 concurrent GPU workers); • Asynchronous HTTP 202 queue buffering to prevent server crash. |
| **5. Third-Party LLM & API Quota Bottlenecks** | Google Gemini 1.5 Flash API could hit rate limit caps (RPM/TPM) during peak platform marketing campaigns. | • In-memory Redis caching for identical prompt expansion requests (TTL 1hr); • Pre-computed style tokens; • Automatic graceful fallback to local template interpolator if LLM API is unavailable. |
| **6. Content Moderation & NSFW Filtration** | Users attempting to input prompt jailbreaks or generate harmful, copyrighted, or NSFW outputs. | • Multi-tier moderation gate: (1) Gemini Safety Settings on Magic Prompt expander, (2) Server-side negative keyword blocklist, and (3) Safety-checker post-processing on GPU inference before saving outputs. |

---

## 16. Phased Implementation Roadmap (8 Weeks / 4 Sprints)

| Sprint | Focus Area | Key Deliverables |
| :--- | :--- | :--- |
| **Sprint 1 (Weeks 1–2)** | Core DRM, Supabase & Paywall | • Supabase PostgreSQL Schema, RLS & Storage Buckets; • In-App Cloud Library; • 2-Credit Idempotent Download Paywall; • 15-Minute Supabase Signed URLs; • Stripe Webhook (`POST /api/v1/wallet/stripe-webhook`); • Mobile `FLAG_SECURE` copy protection |
| **Sprint 2 (Weeks 3–4)** | AI Engine & Pricing | • Complexity Tokenizer & Range Clamping algorithm (`round_half_up`); • Gemini 1.5 Flash Magic Expander; • Self-hosted T4 GPU worker with Pollinations fallback; • Next.js 15 Web Studio Scaffold |
| **Sprint 3 (Weeks 5–6)** | Marketplace & Royalties | • Server-Side AES-256 Prompt DRM; • Anti-Sybil Royalty Transaction Ledger (`purchased_balance` gating); • Explore Masonry Grid & 1-Tap Remix drawer; • Supabase `pgvector` semantic discovery |
| **Sprint 4 (Weeks 7–8)** | Video Suite & Hardening | • LivePortrait neural face motion pipeline; • InstantID face swap pipeline (Apache 2.0); • Next.js 15 SSR Production Build; • Automated CI/CD pipelines & production launch |

---

## 17. Executive Decision Points For Sign-Off

To approve kickoff into Sprint 1 development, alignment is requested on:
1. **Royalty Model:** Confirmation of **Model 1 (Tiered Gamification)** as default setting in remote configuration (with Anti-Sybil purchased credit gating).
2. **Download Paywall Pricing:** Confirmation of **flat 2 Credits ($0.20)** for master unwatermarked file downloads (with free idempotent re-downloading).
3. **Sprint 1 Kickoff:** Authorization to begin engineering implementation of the Supabase schemas, wallet ledger, Stripe webhook, and DRM download paywall across Flutter, Next.js 15, and FastAPI.
