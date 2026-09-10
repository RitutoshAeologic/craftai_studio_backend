# MeiGen Creator Studio — Executive Review & Architecture Summary

> **Document Purpose:** High-level executive review document covering product vision, core business rules, MeiGen feature parity, unit economics, architecture, security, and the 8-week delivery roadmap.  
> **Estimated Review Time:** 5–7 minutes (~3–4 pages in MS Word).  
> **Technology Stack:** Flutter (iOS/Android) • Next.js 15 (Web Platform) • FastAPI (Python) • Supabase (PostgreSQL, Auth, Storage, Realtime, pgvector) • Serverless GPU Workers.

---

## 1. Executive Snapshot & Value Proposition

MeiGen Creator Studio combines an **AI Image & Video Creation Studio** with a **Community Prompt Marketplace** (inspired by MeiGen.ai), deployed across **Flutter Mobile (iOS/Android)** and **Next.js 15 Web**.

### The Problem With Current AI Apps:
1. **Upfront Paywalls:** Demanding money before creation leads to an **85%+ user drop-off**.
2. **Zero Creator Protection:** Popular prompts are easily copied from public feeds, leaving creators unrewarded.

### Our Solution ("The Creator Flywheel"):
* **Free Creation:** Users create and save unlimited images inside their in-app Cloud Library at zero cost.
* **Pay-to-Download:** Exporting high-resolution, unwatermarked 4K master files to the device gallery costs **flat 2 Credits ($0.20)**. Re-downloads of already unlocked images are **100% free (idempotent)**.
* **Anti-Sybil Creator Royalties:** Creators publish prompts to the Explore feed and earn **passive royalties on community remixes** (configurable via Supabase settings). Royalties are strictly funded from *purchased credits* to prevent fake-account cash farming.
* **Guaranteed Uniform Pricing:** AI generation costs scale dynamically with compute complexity, but are strictly capped within **predictable tier brackets (e.g., 1–3 credits)** using explicit `round_half_up` rounding.
* **Server-Side AES-256 Envelope Encryption:** Secret prompts are encrypted with AES-256-GCM; client UI displays aesthetic abstracts only and direct copying is blocked.

---

## 2. The 4 Core Business Rules

| Rule | Mechanism | Business & Technical Value |
| :--- | :--- | :--- |
| **Rule 1: Pay-to-Download (Idempotent)** | In-app creation and cloud library are free. Unlocking high-res 4K files to device gallery requires **2 credits ($0.20)** on first export; subsequent re-downloads are free. | Eliminates user onboarding friction while monetizing high-intent exports without unfair double-charging. |
| **Rule 2: Anti-Sybil Creator Royalties** | Creators earn royalties whenever community members remix their published prompts. Funded strictly via *purchased credits* to block promotional credit farming. | Generates organic user growth; creators actively bring their audience to earn passive income safely. |
| **Rule 3: Range-Bound Dynamic Pricing** | Compute charges adjust by prompt tokens, model, and resolution, but remain strictly locked inside **predefined Min–Max limits**. | Fair compute-based billing without bill shocks or unexpected overcharges. |
| **Rule 4: Server-Side AES-256 DRM** | Prompts are AES-256 encrypted on the server; client UI displays aesthetic abstracts only. Direct copy is blocked on mobile and web. | Protects creators' proprietary prompt recipes from plagiarism without misleading "Zero-Knowledge" claims. |

---

## 3. MeiGen Feature Parity Matrix

Our platform delivers full feature parity with MeiGen.ai across 6 core modules:

| Module | Core Capabilities |
| :--- | :--- |
| **1. Explore & Prompt Gallery** | • Pinterest-style masonry grid feed with semantic **"More like this"** discovery grid powered by **Supabase pgvector**; • Category filters (Anime, Photorealism, Cyberpunk, 3D, Logo); • **Dual-Action Card Drawer:** **`Use as Prompt`** (1-Tap Remix formula) and **`Use as Ref`** (1-Tap Image Reference injection); • Social engagement: Likes, Shares, Creator Profiles |
| **2. AI Image Creation Studio** | • **Consistent Characters & Face Lock:** Save recurring character profiles with **3-angle facial reference photos** (InstantID Apache 2.0); • Multi-reference image slots (`+ Add reference images`); • Interactive Studio Bar: Batch Count (`- 1/4 +`), Seed Lock (`🔒`), Aspect Ratio (`Auto`, 1:1, 9:16, 16:9), Resolution (`2K / 4K`); • Dynamic button: `Generate ✨ {credits}` |
| **3. In-Prompt AI Actions & Expander** | • **`Enhance` (Magic Expander):** Gemini 1.5 Flash studio expansion (<200ms); • **`✨ AI Edit`:** Instructed image modification with Subject Lock (`EDIT THE PROVIDED PHOTO — ABSOLUTE LOCK`); • Photo-to-Prompt vision scanner |
| **4. Dedicated AI Video Suite** | • Image-to-Video (I2V) and Text-to-Video (T2V); • LivePortrait Face Motion (Smile, Wink, Talk, Head Movement via preset animations & user driving video); • Camera controls (Pan, Tilt, Zoom, 3D Orbit); • 3s & 5s durations |
| **5. Creative Skills Toolbox** | • AI Background Remover (Transparent PNG); • Portrait Relighting & Bokeh Blur; • 4K Lossless Upscaler; • Face Swap & Re-Aging (InstantID / ReActor — **Apache 2.0 Commercial License**) |
| **6. Cloud Library & Creator Dashboard** | • Unlimited private cloud storage in Supabase; • Custom collections/folders; • Paginated library sync (`GET /api/v1/users/me/library`); • Creator analytics (Remix count, earnings, payout request) |

### Automated Prompt Engineering Pipeline (How Prompts Are Generated)
Everyday users don't know complex prompts. The system converts raw ideas into studio outputs via a **4-Stage Pipeline**:
1. **User Input Channel:** (A) Direct text (e.g., *"samurai girl"*), (B) Smart variable chips (`[character]`, `[clothing]`), (C) Consistent Character profile (3-angle face lock), or (D) Reference photo scan (Gemini Vision).
2. **Magic Prompt Expansion (<200ms):** Google Gemini 1.5 Flash injects camera lens (85mm f/1.4), cinematic lighting, volumetric smoke, and 8K render fidelity.
3. **Negative Prompt Injection (Server-side):** Server silently appends anti-distortion tokens (`bad anatomy, extra fingers, mutated hands, blurry, watermark`).
4. **Concrete Transformation:**
   * *Raw User Input:* `"samurai girl in neon city"`
   * *Generated Studio Prompt:* `"Cinematic medium portrait of a female ronin in dark cyberpunk kimono, wet asphalt Neo-Tokyo street, reflecting neon magenta lights, 85mm f/1.4 lens, 8k, photorealistic textures."`
   * *Execution:* Master prompt is encrypted with AES-256 and passed in-memory to serverless GPU workers (Flux/SDXL).

---

## 4. Financial Model & Unit Economics (98%+ Margins)

* **Credit Value:** 10 Credits = $1.00 USD (**1 Credit = $0.10 USD / ~₹8.5 INR**).
* **Cost vs. Revenue Breakdown (Including Storage Egress):**

| Action | Credits Charged | User Pays | Cloud Cost | Gross Profit | Net Margin (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Basic Image (Flux)** | 2 Credits | $0.200 | $0.0020 | **$0.1980** | **99.0%** |
| **Standard HD (SDXL)** | 4 Credits | $0.400 | $0.0050 | **$0.3950** | **98.7%** |
| **Community Remix\*** | 5 Credits | $0.500 | $0.0050 | **$0.2950** | **59.0% Net** |
| **Download 4K Master** | 2 Credits | $0.200 | $0.0025 (Egress) | **$0.1975** | **98.7%** |
| **LivePortrait Video** | 10 Credits | $1.000 | $0.0150 | **$0.9850** | **98.5%** |

*\*Assumes 40% creator royalty ($0.20 paid to creator, $0.30 retained by platform, leaving 59% net margin after compute cost).*

---

## 5. Creator Royalty Policy: 4 Proposed Models

> **Implementation Note:** The royalty split is **not hardcoded**. It is a dynamic backend parameter (managed via Supabase `app_settings` / FastAPI configuration), allowing instant updates without app redeployment.

1. **Model 1: Tiered Gamified Split (Recommended)**
   * Bronze (< 100 remixes): **20% Creator / 80% Platform**
   * Silver (100–500 remixes): **30% Creator / 70% Platform**
   * Gold (500–2,000 remixes): **40% Creator / 60% Platform**
   * Diamond (> 2,000 remixes): **50% Creator / 50% Platform**
   * *Strategic Value:* Gamification motivates creators to share their links externally. Platform keeps an **80% margin on early-tier creators**.
2. **Model 2: Flat Configurable Split (Baseline Proposal)**
   * A single platform-wide percentage (e.g., 30%, 40%, or 50%) applied uniformly. Simple to communicate.
3. **Model 3: Fixed Credit Bounty (Compute-Safe)**
   * Flat 1 or 2 Credits paid to creator per remix regardless of model complexity. Protects margins against GPU cost changes.
4. **Model 4: Creator Markup (Open Marketplace)**
   * Creators set their own extra credit markup (1–5 credits) over base cost; platform takes a 20% marketplace fee.

---

## 6. Architecture & Technology Division of Labor

* **Mobile Client:** Flutter (iOS 15+, Android SDK 21–36) with `supabase_flutter` for Auth, Realtime streams, and native DRM (`FLAG_SECURE`).
* **Web Client:** Next.js 15 (React, TypeScript, App Router) with Server-Side Rendering (SSR) for SEO-indexed prompt discovery and WebGL canvas.
* **Compute Gateway:** FastAPI (Python 3.11) ➔ Asynchronous Task Queue ➔ Serverless GPU Workers (RunPod / Modal / T4).
* **Database & Cloud:** Supabase (PostgreSQL 15+, Row Level Security, Realtime WebSockets, pgvector, and S3-compatible Storage).

### Who Does What:
* **Flutter Mobile App:**
  - ScreenUtil responsive engine (`.w`, `.h`, `.sp`) with zero RenderFlex overflow.
  - Native DRM: Android `FLAG_SECURE` and iOS screen capture detection.
  - Supabase Realtime client: updates generation progress in <50ms.
* **Next.js 15 Web Platform:**
  - High-performance desktop studio and public marketplace.
  - Server-Side Rendering (SSR) for prompt discovery and search engine indexability.
  - Canvas-based DRM protection and anti-scraping event interceptors.
* **FastAPI (Python Compute Gateway):**
  - Non-blocking auth verification using Supabase JWT tokens (`def get_current_user`).
  - Stripe webhook handler (`POST /api/v1/wallet/stripe-webhook`) for credit pack fulfillment.
  - Complexity Tokenizer & Dynamic Price Clamping (using `round_half_up`).
  - Gemini 1.5 Flash Magic Prompt Expansion (<200ms).
  - AES-256 Prompt Envelope Encryption / Decryption.
  - Automated EXIF metadata stripping before writing public previews.
  - Supabase Storage Signed Download URL generation with **15-minute (900s) TTL** for reliable mobile downloads.
* **Supabase (PostgreSQL Database, Auth, Realtime & Storage):**
  - **Supabase Auth:** Google, Apple, Email, and Anonymous SSO with JWTs.
  - **PostgreSQL Database:** ACID relational transactions with Row-Level Locking (`SELECT ... FOR UPDATE`) and Row Level Security (RLS).
  - **`pgvector` Extension:** Direct vector similarity search for the **"More like this"** discovery grid.
  - **Supabase Realtime:** WebSocket CDC (Change Data Capture) streaming job completion to Flutter and Next.js in **<50ms** without client polling.
  - **Supabase Storage:** Two-tier S3-compatible buckets (`previews` CDN bucket for WebP; `masters` private bucket for 4K PNGs).
* **Asynchronous Queue:**
  - Fast HTTP 202 ACK on generation requests. Background GPU workers process jobs asynchronously; client UI remains completely non-blocking.

---

## 7. Security, Licensing & Anti-Abuse: 7 Core Protections

| Attack Vector / Loophole | Risk Description | Production Solution |
| :--- | :--- | :--- |
| **1. Sybil Royalty Farming** | Scripting 500 fake accounts using free signup credits to remix an author's prompt and extract cash. | **Purchased-Credit Gating**. Royalties are strictly credited only if payment is deducted from `purchased_balance`. Free/promo credits yield 0 cash royalty. |
| **2. Double-Spend Race** | Rapid concurrent taps attempting to spend 3 credits on 10 parallel jobs. | **PostgreSQL ACID Lock (`SELECT ... FOR UPDATE`) + Redis Distributed Lock**. Concurrent calls queue or reject safely. |
| **3. Re-Download Overcharge** | Users getting recharged 2 credits when re-downloading an already unlocked image after link expiry. | **Idempotent Unlock Check**. Backend checks `job.is_download_unlocked`; if True, skips deduction and serves signed URL for free. |
| **4. Expired Mobile Downloads** | 60-second signed URL expiring mid-transfer on slow 3G/4G connections for 20MB files. | **15-Minute (900s) Signed URL TTL**. Sufficient window for large mobile transfers via Supabase Storage without exposing persistent links. |
| **5. Commercial Licensing Risk** | Using non-commercial research models (e.g. InsightFace) in a commercial SaaS app. | **Permissive Licensing**. Using **InstantID (Apache 2.0)** and **ReActor / CodeFormer** for 100% legal commercial compliance. |
| **6. EXIF Metadata Leak** | Diffusion models embedding raw prompts inside image metadata headers. | **Automated EXIF Purge**. Backend strips all metadata (`exif=b""`) before writing public previews. |
| **7. Platform DRM Security** | Preventing screenshots and prompt theft across platforms. | **Native Mobile DRM** (`FLAG_SECURE` on Android, `UIScreen.capturedDidChangeNotification` on iOS) + Canvas DOM obfuscation on Next.js Web. |

---

## 8. Technical Challenges, System Limitations & Mitigations

| Key Challenge / Limitation | Impact & Risk | Engineering Mitigation |
| :--- | :--- | :--- |
| **1. GPU Cold Starts (Serverless Latency)** | Model weights (12–24GB) take 15–25s to load when spinning up a new GPU worker during traffic spikes. | Min-concurrency warm instance during peak hours + NVMe cached weights + instant 5s failover to Pollinations fallback. |
| **2. Mobile Network 4K Downloads** | 20MB 4K PNG exports risk network timeout on spotty 3G/4G cellular connections. | 15-Minute (900s) Signed URL TTL + resumable chunked downloads + free idempotent re-downloads via Supabase Storage. |
| **3. Web Browser DRM Constraints** | Unlike mobile (`FLAG_SECURE`), browsers cannot 100% block external phone cameras or OS screen capture. | Master prompt ciphers strictly kept server-side; Next.js uses Canvas DOM obfuscation & right-click blocks; only chips exposed. |
| **4. GPU Cost Overrun on Viral Prompts** | A viral prompt could trigger thousands of concurrent remix calls, risking runaway serverless compute bills. | Token-Bucket rate limiting (max 5 active jobs/user) + global auto-scale cap (max 20 workers) + HTTP 202 queue buffering. |
| **5. Third-Party LLM Quota Bottlenecks** | Gemini 1.5 Flash API could hit rate limit quotas during platform-wide viral marketing campaigns. | In-memory Redis response caching (1hr TTL) + graceful local fallback to pre-computed style templates. |
| **6. Content Moderation & Abuse** | Malicious users attempting prompt jailbreaks, NSFW generation, or deepfakes. | Multi-tier moderation: Gemini safety settings + server-side keyword blocklist + GPU post-inference safety filters. |

---

## 9. Implementation Roadmap (8 Weeks / 4 Sprints)

| Sprint | Focus Area | Key Deliverables |
| :--- | :--- | :--- |
| **Sprint 1 (Weeks 1–2)** | Core DRM, Supabase & Paywall | • Supabase PostgreSQL Schema, RLS & Storage Buckets; • In-App Cloud Library; • 2-Credit Idempotent Download Paywall; • 15-Minute Supabase Signed URLs; • Stripe Webhook (`POST /api/v1/wallet/stripe-webhook`); • Mobile `FLAG_SECURE` copy protection |
| **Sprint 2 (Weeks 3–4)** | AI Engine & Pricing | • Complexity Tokenizer & Range Clamping algorithm (`round_half_up`); • Gemini 1.5 Flash Magic Expander; • Self-hosted T4 GPU worker with Pollinations fallback; • Next.js 15 Web Studio Scaffold |
| **Sprint 3 (Weeks 5–6)** | Marketplace & Royalties | • Server-Side AES-256 Prompt DRM; • Anti-Sybil Royalty Transaction Ledger (`purchased_balance` gating); • Explore Masonry Grid & 1-Tap Remix drawer; • Supabase `pgvector` semantic discovery |
| **Sprint 4 (Weeks 7–8)** | Video Suite & Hardening | • LivePortrait neural face motion pipeline; • InstantID face swap pipeline (Apache 2.0); • Next.js 15 SSR Production Build; • Automated CI/CD pipelines & production launch |

---

## 10. Executive Decision Points For Sign-Off

To move into Sprint 1 development, the following 3 items are ready for alignment:
1. **Royalty Split Model:** Approval of **Model 1 (Tiered Gamification)** vs. **Model 2 (Flat Split)** as initial default setting (with Anti-Sybil purchased credit gating).
2. **Download Paywall Pricing:** Confirmation of **flat 2 Credits ($0.20)** for master unwatermarked file downloads (with free idempotent re-downloading).
3. **Sprint 1 Kickoff:** Approval of core architecture (Flutter + Next.js 15 + FastAPI + Supabase) to begin implementation of the database schemas, wallet ledger, Stripe webhook, and DRM download paywall.
