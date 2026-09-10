# MeiGen Creator Studio — Quick Review Summary (Aasan Hindi / Hinglish)

> **Document Ka Maqsad:** MeiGen Creator Studio ka high-level review summary jisme business model, 4 core rules, MeiGen features, profit margins, backend architecture, aur 8-week delivery plan shamil hain.  
> **Review Ka Time:** 5 se 7 minute (MS Word mein lagbhag 3 se 4 page).  
> **Tech Stack:** Flutter Mobile App (iOS/Android) • Next.js 15 (Web Platform) • FastAPI (Python Gateway) • Supabase (PostgreSQL Database, Auth, Storage & Realtime) • Serverless GPU Workers.

---

## 1. Project Ka Pura Concept (Quick Snapshot)

Ye app **MeiGen.ai** jaisi ek **AI Image & Video Creation App + Creator Marketplace** hai, jo **Flutter Mobile App** aur **Next.js 15 Web Platform** dono par chalegi.

### Market Ki Purani Apps Ki 2 Badi Galtiyan:
1. **Shuru Mein Hi Paise Maangna:** Prompt likhte hi payment mangne par **85%+ users app band karke delete kar dete hain**.
2. **Prompts Ki Chori:** Public feed se koi bhi prompt copy kar leta hai, aur prompt banane wale creator ko kuch nahi milta.

### Hamara Solution (Creator Flywheel):
* **Image Creation Bilkul Free:** User app ke andar unlimited images bana sakta hai jo uski in-app Cloud Library mein safe rahengi.
* **Gallery Download Par Charge (Rule 1):** Phone ki gallery mein bina watermark wali 4K original file download karne ke **flat 2 Credits ($0.20 ya ~₹17)** lagenge. Ek bar unlock hone ke baad re-download hamesha **100% Free** rahega (dobara charge nahi lagega).
* **Anti-Fraud Creator Royalties (Rule 2):** Creator apna prompt publish karega aur jab koi dusra user remix (use) karega, tab **creator ko royalty kamayi milegi**. Fake accounts se bachne ke liye royalty sirf tabhi banegi jab user ne *real paise se credits khareede hon* (free bonus credits se cash royalty nahi nikaali ja sakti).
* **Guaranteed Uniform Pricing (Rule 3):** Kitne credits lagenge ye prompt aur model par depend karega, lekin **ek guaranteed limit (jaise 1–3 credits) ke andar hi rahega**.
* **Secret Prompt Protection (Rule 4):** Prompt text copy karna block hai. Original prompt server par AES-256 password lock se safe rehta hai.

---

## 2. Platform Ke 4 Mukhya Niyam (Core Rules)

| Niyam (Rule) | Ye Kaise Kaam Karta Hai? | Business & Tech Fayda |
| :--- | :--- | :--- |
| **Rule 1: Pay-to-Download (Idempotent)** | App ke andar creation aur cloud library free hai. Phone mein 4K master file save karne par **pehli baar 2 credits ($0.20)** lagenge; dubara download karne par ₹0 (free). | Naye users shuru mein hi nahi bhagte, aur unse double charging nahi hoti. |
| **Rule 2: Anti-Fraud Creator Royalties** | Jab bhi koi community member kisi creator ka prompt remix karega, **creator ko uski kamayi ka hissa milega**. Ye sirf *purchased balance* se katega taaki fake accounts se koi cash na nikaal sake. | Creators khud apne social media par app ko promote karenge taaki unki passive income bane. System fraud se 100% safe rahega. |
| **Rule 3: Range-Bound Dynamic Pricing** | Prompt ki lambai aur resolution ke hisab se compute cost adjust hogi, par **har category ki ek Min–Max limit pehle se fix hogi**. | Fair billing: Chhote prompt ka kam, bade ka thoda zyada, par kabhi anjaana bada bill nahi aayega. |
| **Rule 4: Server-Side AES-256 DRM** | Public feed par sirf photo aur basic description dikhega. Asli formula server par AES-256 password lock se safe rahega. | Creators ka secret prompt formula internet par copy ya chori nahi ho sakta. |

---

## 3. MeiGen Ke Saare Features (Parity Matrix)

Hamari app mein MeiGen.ai ke saare 6 zaroori modules shamil hain:

| Module | Kya-Kya Features Honge? |
| :--- | :--- |
| **1. Explore & Prompt Gallery** | • Pinterest jaisa smooth scrolling masonry feed sath mein **Supabase pgvector** se chalne wala **"More like this"** recommendations; • Category filters (Anime, Real Photo, Cyberpunk, 3D, Logo); • **Dual-Action Buttons:** **`Use as Prompt`** (Remix formula) aur **`Use as Ref`** (Photo ko reference image banana); • Social engagement: Likes, Shares, Creator Profiles |
| **2. AI Image Creation Studio** | • **Consistent Characters & Face Lock:** 3-angle facial reference photos (Front, 45°, Side) se apna ya model ka chehra hamesha ke liye lock karna; • Reference image slots (`+ Add reference images`); • Studio Bar: Batch Count (`- 1/4 +`), Seed Lock (`🔒`), Aspect Ratio (`Auto`, 1:1, 9:16, 16:9), Resolution (`2K / 4K`); • Button: `Generate ✨ {credits}` |
| **3. In-Prompt AI Actions** | • **`Enhance` (Magic Expander):** Gemini 1.5 Flash studio prompt expansion (<200ms); • **`✨ AI Edit`:** Uploaded photo par chehra lock rakhkar kapde ya background badalna (`ABSOLUTE LOCK`); • Photo-to-Prompt scanner |
| **4. Dedicated AI Video Suite** | • Photo se video banana (Image-to-Video); • LivePortrait Face Motion (Selfie se smile, wink, bolna, sar hilana via preset animation ya reference video); • Camera controls (Pan, Tilt, Zoom, 3D Orbit); • 3s aur 5s clips |
| **5. Creative Skills Toolbox** | • AI Background Remover (Transparent PNG); • Portrait Relighting aur DSLR blur; • 4K Lossless Upscaler; • Face Swap aur Age changer (**InstantID / ReActor — 100% Legal Commercial License**) |
| **6. Cloud Library & Creator Dashboard** | • Unlimited private cloud storage Supabase mein; • Custom collections/folders; • Paginated library sync (`GET /api/v1/users/me/library`); • Creator analytics (Remix count, kamayi, bank payout) |

### Prompt Kaise Generate Hota Hai? (Automated 4-Step Pipeline)
Aam user ko prompt engineering nahi aati, isliye system raw input ko **4 steps mein studio prompt mein badalta hai**:
1. **User Ka Input:** (A) Direct 2-3 words (jaise *"samurai girl"*), (B) Dropdown chips (`[character]`, `[kapde]`), (C) Saved Character Profile (3-angle face lock), ya (D) Reference photo scan (Gemini Vision).
2. **Magic Prompt Expansion (<200ms):** Google Gemini 1.5 Flash camera lens (85mm f/1.4), cinematic lighting, volumetric smoke aur 8K details khud jod deta hai.
3. **Negative Prompt Injection (Server Filter):** Backend chupke se negative tags jodta hai (`bad anatomy, 6 fingers, blurry, watermark`) taaki photo kharab na bane.
4. **Real Example (Before vs After):**
   * *User Ne Likha:* `"samurai girl in neon city"`
   * *System Ne Banaya:* `"Cinematic portrait of female ronin in cyberpunk kimono, wet asphalt Neo-Tokyo street, reflecting neon magenta lights, 85mm f/1.4 lens, 8k, hyper-detailed."`
   * *Execution:* Master prompt AES-256 se encrypt hokar serverless GPU (Flux/SDXL) ke paas execute hone chala jaata hai.

---

## 4. Business Unit Economics (98%+ Profit Margins)

* **1 Credit Ki Keemat:** 10 Credits = $1.00 USD (**1 Credit = $0.10 USD / ~₹8.5 INR**).

| User Ka Action | Credits Kaate | User Ne Kitne Diye | Hamara Server Kharcha | Hamara Net Munafa | Profit Margin (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Basic Image (Flux)** | 2 Credits | $0.200 | $0.0020 | **$0.1980** | **99.0%** |
| **Standard HD (SDXL)** | 4 Credits | $0.400 | $0.0050 | **$0.3950** | **98.7%** |
| **Community Remix\*** | 5 Credits | $0.500 | $0.0050 | **$0.2950** | **59.0% Net** |
| **Download 4K Master** | 2 Credits | $0.200 | $0.0025 (Bandwidth) | **$0.1975** | **98.7%** |
| **LivePortrait Video** | 10 Credits | $1.000 | $0.0150 | **$0.9850** | **98.5%** |

*\*Remix par 40% creator royalty kaatne ke baad ($0.20 creator ko, $0.30 platform ke paas), compute cost nikaal kar bhi 59% net munafa bachta hai.*

---

## 5. Creator Royalty Policy Ke 4 Proposed Models

> **Important:** Royalty percentage ko code mein hardcode nahi kiya gaya hai. Ye Supabase backend settings (`app_settings` table) se bina app update kiye dynamically change ho sakti hai.

1. **Model 1: Level Ke Hisab Se Royalty (Tiered Gamification - Recommended)**
   * Bronze (< 100 remixes): **20% Creator / 80% Platform**
   * Silver (100–500 remixes): **30% Creator / 70% Platform**
   * Gold (500–2,000 remixes): **40% Creator / 60% Platform**
   * Diamond (> 2,000 remixes): **50% Creator / 50% Platform**
   * *Business Fayda:* Creators apna level badhane ke liye khud promote karenge. Naye creators par platform ko **80% margin** bachega.
2. **Model 2: Flat Configurable Split (Baseline Proposal)**
   * Sabhi creators par ek flat percentage (jaise 30%, 40%, ya 50%) apply hogi. Simple aur clear rule.
3. **Model 3: Fixed Credit Bounty (Compute-Safe)**
   * Har remix par creator ko flat **1 ya 2 Credits** milenge, chahe koi bhi model use ho. Server cost badhne par bhi safe.
4. **Model 4: Creator Markup (Open Marketplace)**
   * Creator khud apna margin (1–5 credits) set karega; platform us margin par 20% cut lega.

---

## 6. Architecture & System Flow (Flutter + Next.js 15 + FastAPI + Supabase)

* **Mobile App:** Flutter Mobile App (iOS 15+, Android SDK 21–36) with native DRM (`FLAG_SECURE`).
* **Web Platform:** Next.js 15 (React, TypeScript, App Router) with Server-Side Rendering (SSR) for SEO and explore marketplace.
* **API Gateway:** FastAPI (Python 3.11) ➔ Asynchronous Queue ➔ Serverless GPU Workers (RunPod / Modal / T4).
* **Database & Cloud:** Supabase (PostgreSQL 15+, Row Level Security, Realtime WebSockets, pgvector, and S3-compatible Storage).

### Kaun Kya Sambhalega?
* **Flutter Mobile App:**
  - Responsive ScreenUtil layout jisse kisi bhi phone par screen overflow na ho.
  - Native screenshot aur screen record protection (`FLAG_SECURE`).
  - Supabase Realtime se direct connection: photo bante hi screen update.
* **Next.js 15 Web Platform:**
  - Desktop studio aur public prompt marketplace.
  - Server-Side Rendering (SSR) taaki Google search par marketplace rank kare.
  - Canvas protection aur right-click blocking taaki prompt chori na ho.
* **FastAPI (Python Compute Gateway):**
  - Non-blocking authentication verification using Supabase JWT tokens.
  - Stripe payment webhook (`POST /api/v1/wallet/stripe-webhook`) automatic credit recharge ke liye.
  - Prompt analyze karna aur correct credits calculate karna (`round_half_up`).
  - Gemini AI se magic prompt expansion karwana (<200ms).
  - AES-256 prompt encryption aur decryption.
  - EXIF hidden metadata hatana taaki prompt leak na ho.
  - Supabase Storage ke zariye **15-minute (900 seconds) valid download links** banana taaki slow net par bhi 20MB file fail na ho.
* **Supabase (PostgreSQL Database, Auth, Realtime & Storage):**
  - **Supabase Auth:** Google, Apple, Email, aur Guest SSO login.
  - **PostgreSQL Database:** Ekdum pakka ACID transaction system with Row-Level Lock (`SELECT ... FOR UPDATE`) aur Row Level Security (RLS).
  - **`pgvector` Extension:** Direct database ke andar vector similarity search jo **"More like this"** discovery feed chalata hai.
  - **Supabase Realtime:** WebSocket streams jisse photo complete hote hi **<50ms mein screen par aa jaati hai** (polling ki zaroorat nahi).
  - **Supabase Storage:** Master 4K files private bucket mein aur preview images fast CDN bucket par.
* **Background Queue:**
  - Generation request aate hi server turant accept kar leta hai. Phone/Web screen freeze nahi hoti; background GPU kaam karta hai aur photo bante hi screen update ho jaati hai.

---

## 7. Security, Licensing & Anti-Abuse: 7 Core Protections

| Vulnerability / Khatra | Khatra Kya Hai? | Production Ilaaj |
| :--- | :--- | :--- |
| **1. Fake Account Royalty Scam** | 500 fake accounts banakar free signup credits se apne hi prompt ko remix karke cash nikalna. | **Purchased Credit Rule**. Royalty sirf tabhi banegi jab remix karne wale ne paise se credit khareede hon. Free credits se cash royalty zero banegi. |
| **2. Double-Spend Race** | 3 credit ke wallet se ek sath 10 tap karke 10 photos generate kar lena. | **PostgreSQL ACID Lock (`SELECT ... FOR UPDATE`) + Redis Lock**. Ek time par ek hi deduction hoga. |
| **3. Re-Download Double Charge** | Ek bar 2 credit dekar unlock ki hui image ka link expire hone par dubara paise kat jana. | **Idempotent Unlock Check**. Backend pehle check karega agar `is_download_unlocked == True` hai toh ₹0 (free) mein naya link de dega. |
| **4. Slow Mobile Download Failure** | 60-second ka link 3G/4G network par 20MB 4K photo download hone se pehle hi expire ho jana. | **15-Minute (900s) Download Link TTL**. Supabase Storage se mobile network par file aaram se aur bina fail huye download hogi. |
| **5. Commercial Legal Risk** | Non-commercial research model (jaise InsightFace) commercial app mein use karne par copyright lawsuit ka darr. | **100% Commercial Open Source Models**. Face swap ke liye **InstantID (Apache 2.0 License)** aur **ReActor** use hoga. |
| **6. EXIF Data Leak** | Image ke andar chhupe huye background data se secret prompt chori hona. | **Automated EXIF Purge**. Save karne se pehle sara metadata saaf kar diya jaata hai. |
| **7. Screenshot & Copy Protection** | App ke andar se prompt formula chori karna ya screen capture karna. | **Native Mobile DRM** (Android par `FLAG_SECURE`, iOS par screen capture detection) + Next.js Web par right-click block. |

---

## 8. Mukhya Challenges, Limitations Aur Unka Samadhan

Har real-world AI platform mein kuch technical challenges aate hain. Humne unka pehle se pakka solution banaya hai:

| Challenge / Limitation | Asli Problem Kya Hai? | Hamara Production Ilaaj |
| :--- | :--- | :--- |
| **1. GPU Cold Start (Serverless Shuru Hone Mein Time)** | Jab traffic achanak badhta hai, naya GPU worker start hone aur 15GB model load karne mein 15-25s lag sakte hain. | Din ke peak time 1 warm GPU standby rahega; fast NVMe storage cache use hoga; 5s se zyada delay par backup service par instant transfer. |
| **2. Slow Network Par 4K Photo Download** | 20MB ki badi file 3G/4G network par slow download hone par link expire ho sakta hai. | Link ka validity time 15 minute (900s) rakha gaya hai via Supabase Storage; background download manager; dubara download hamesha free. |
| **3. Web Browser DRM Ki Limitations** | Mobile app mein toh screenshot block (`FLAG_SECURE`) ho jata hai, par web browser mein dusre phone se photo khinchne se 100% nahi roka ja sakta. | Master prompt server par hi rehta hai, web par kabhi bheja hi nahi jata; Next.js web par right-click disabled rehta hai; sirf image aur basic tags dikhte hain. |
| **4. Viral Prompts Par GPU Ka Extra Kharcha** | Agar koi prompt viral ho gaya aur hazaron log ek sath remix karne lage, toh server ka bill achanak badh sakta hai. | Rate limiter (ek user ke max 5 active jobs); max 20 GPU workers ki ceiling limit taaki company ka budget safe rahe. |
| **5. Third-Party AI API Ka Quota Khatam Hona** | Google Gemini API ka per-minute quota viral marketing ke time limit cross kar sakta hai. | Ek jaise prompts ko Redis mein 1 ghante tak cache karke rakhna; API busy hone par local smart template se prompt banana. |
| **6. Galat / NSFW Content Rokna** | Kuch users galat ya deepfake photos banane ki koshish kar sakte hain. | 3-Layer Filter: (1) Gemini AI safety settings, (2) Server par blacklisted words, (3) GPU output par automatic safety checker. |

---

## 9. Implementation Timeline (8 Hafte / 4 Sprints)

| Sprint | Kaam Ka Focus | Deliverables (Kya Bankar Ready Hoga) |
| :--- | :--- | :--- |
| **Sprint 1 (Hafte 1–2)** | Core DRM, Supabase & Paywall | • Supabase PostgreSQL Schema, RLS & Storage Buckets; • In-App Cloud Library; • 2-Credit Idempotent Download Paywall; • 15-Minute secure download links; • Stripe Payment Webhook; • Mobile `FLAG_SECURE` copy protection |
| **Sprint 2 (Hafte 3–4)** | AI Engine & Pricing | • Complexity Tokenizer aur Range Clamping logic (`round_half_up`); • Gemini 1.5 Flash Magic Expander; • Fast GPU worker aur backup service; • Next.js 15 Web Studio scaffold |
| **Sprint 3 (Hafte 5–6)** | Marketplace & Royalties | • Server-Side AES-256 Prompt DRM; • Anti-Sybil Royalty Transaction Ledger (`purchased_balance` check); • Explore Grid aur 1-Tap Remix bottom popup; • Supabase `pgvector` recommendations |
| **Sprint 4 (Hafte 7–8)** | Video Suite & Launch | • LivePortrait face motion pipeline; • InstantID face swap pipeline (Apache 2.0); • Next.js 15 SSR live deployment; • Automated CI/CD pipelines & production launch |

---

## 10. Decision Points (Sign-Off Ke Liye 3 Mukhya Points)

Sprint 1 shuru karne ke liye ye 3 points finalize karne hain:
1. **Royalty Model:** Kya **Model 1 (Tiered Gamification)** ko default model choose kiya jaye (jisme Anti-Fraud purchased credit rule active rahega)?
2. **Download Paywall:** Kya 4K master file download ke liye **flat 2 Credits ($0.20 / ₹17)** confirm hain (aur unka re-download hamesha free rahega)?
3. **Sprint 1 Kickoff:** Supabase database schema, Stripe webhook, aur DRM paywall ka development start karne ki approval.
