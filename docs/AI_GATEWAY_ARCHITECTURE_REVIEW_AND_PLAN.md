# CraftAI Studio — Multi-Provider AI Gateway: Architecture Review, Loopholes & Final Adoption Plan

**Document Purpose:** Technical review of the TL's Multi-Provider AI Image Generation & Template Composition proposal against our existing `craftai_studio_backend`, `craftai_studio_web`, `craftai_studio_mobile`, and Supabase PostgreSQL schema.  
**Decision Framework:** Categorizes every proposed component into:
1. **✅ ADOPT AS-IS** — Strong patterns we will implement directly.
2. **🛠️ FIX & ADOPT** — Good ideas that need loophole fixes, alternatives, or schema alignment before adoption.
3. **❌ DO NOT ADOPT** — Proposals that conflict with our live system, add unnecessary cost/bloat, or duplicate working infrastructure.

---

## Executive Decision Matrix

| Area | TL Proposal | Final Decision | Reason / Action |
|---|---|---|---|
| **AI Routing Strategy** | OpenRouter (Text) + Direct APIs (Image) | **✅ ADOPT** | Preserves native image controls (inpainting, masks, references, aspect ratios). |
| **Provider Abstraction** | `ImageProvider` ABC + `ProviderRegistry` | **✅ ADOPT** | Clean upgrade over hardcoded `HuggingFaceClient()` inside `diffusion_factory.py`. |
| **Model Config JSON** | DB/JSON-driven `image_models` catalog | **🛠️ FIX & ADOPT** | Adopt pattern; fix fake model IDs (`gpt-image-1.5`/`2.5`) & add `supports_facelock`, `supports_negative_prompt`, `aspect_ratio_map`. |
| **Face-Lock / Remix** | Missing from TL proposal | **🛠️ ADD (CRITICAL)** | CraftAI's core Selfie-to-Template flow requires dedicated `PuLID` / `InstantID` routing. |
| **OpenRouter Flow** | Forced on every generation request | **🛠️ FIX (ALTERNATIVE)** | Make conditional (`enhance_prompt: bool = False`); bypass for curated trending templates to save 2–4s latency & prevent prompt drift. |
| **Template Engine** | Playwright + Chromium inside FastAPI | **🛠️ FIX (ALTERNATIVE)** | Replace in-process Chromium with **Pillow + CairoSVG** (or Client Canvas + separate isolated worker) to prevent OOM & SSRF. |
| **Billing & Usage Logs** | `ai_usage_logs` + `idempotency_key` + Reserve/Refund | **🛠️ FIX & ADOPT** | Adopt `ai_usage_logs` & `idempotency_key`; add **Reservation TTL Reaper** + **Creator Royalty** support on existing `wallets`. |
| **Backend Folder Rewrite** | New `app/modules/...` & new endpoints | **❌ DO NOT ADOPT** | Keep existing `app/api/v1/router.py`, `app/services/`, `app/infrastructure/clients/` so Web & Mobile don't break. |
| **Duplicate DB Tables** | New `user_credits`, `generated_images` | **❌ DO NOT ADOPT** | Keep existing `wallets`, `wallet_ledger`, `generations`, `explore_prompts`; extend via incremental migration. |
| **Local AI Tools** | Route all edits to Gemini 2.5 Flash Image | **❌ DO NOT ADOPT** | Keep existing zero-API-cost `app/infrastructure/tools/` (`bg_remover`, `upscaler`, `lama_inpaint`, `ddcolor`). |

---

## 1. ✅ What We Will ADOPT (High-Value Proposals)

1. **Hybrid Provider Architecture:**
   * **Text Intelligence:** OpenRouter (for prompt classification, delta refinement, and structured edit-intent parsing) with fallback to our existing Gemini/Groq clients.
   * **Image Generation & Editing:** Direct provider adapters (`fal.ai`, `OpenAI`, `Google Gemini`) so we never lose native parameters like multi-image references, masks, transparency, or quality tiers.
2. **`ImageProvider` Interface & `ProviderRegistry` Pattern:**
   * Every provider adapter implements a strict common contract (`generate`, `edit`, `get_job_status`) and raises explicit capability errors when an operation isn't supported (no silent wrong fallbacks).
3. **Config-Driven Model Catalog (`ai_providers` & `ai_models`):**
   * Moving model selection, pricing, and enabled/disabled toggles into PostgreSQL/Supabase (`ai_models` table + `ConfigService` 60s cache) instead of hardcoding model strings in code.
4. **`ai_usage_logs` Telemetry Table:**
   * Currently we track user credit deductions in `wallet_ledger`, but not actual provider API cost (`input_tokens`, `output_tokens`, `image_count`, `resolution`, `cost`, `currency`). Adding `ai_usage_logs` gives exact profit/margin visibility per model.
5. **Separation of Image Generation vs. Template Composition:**
   * AI models should only generate/edit the visual asset; text overlays, brand logos, and marketing layouts belong in a deterministic composition layer.
6. **Non-Destructive Image Versioning:**
   * Saving edited outputs as new asset rows linked to the original (`parent_generation_id` / `image_edit_history`) rather than overwriting original images.

---

## 2. 🛠️ What We Will FIX & ADOPT (Loopholes & Alternative Solutions)

### Fix 1: Verify Live Model IDs & Strip Unsupported Parameters
* **Loophole in TL Proposal:**
  * `GPT Image 1.5` and `GPT Image 2.5` are not standard live public API model IDs (OpenAI's live native image model is `gpt-image-1`).
  * TL's enhanced prompt outputs `negative_prompt`, but **FLUX.1 Schnell**, **GPT Image**, and **Gemini Flash Image** do not accept `negative_prompt` natively—passing it blindly causes `422` errors or silent failures.
* **Fix:**
  * Verify exact live endpoints before seeding `ai_models`:
    * Economy Draft: `fal-ai/flux/schnell` (fal.ai)
    * Standard Prompt-to-Image / Edit: `gpt-image-1` (OpenAI)
    * Natural-Language Image Edit: `gemini-2.5-flash-image` (Google)
    * Face-Lock Remix: `fal-ai/flux-pulid` or `InstantID` (fal.ai)
  * Add capability flags (`supports_negative_prompt`, `supports_facelock`, `supports_transparency`) and an **`aspect_ratio_map`** inside each `ai_models` record so the adapter strips unsupported params and translates `"16:9"` into provider-exact formats (`"1536x1024"` for OpenAI vs `"landscape_16_9"` for fal.ai).

---

### Fix 2: Add Face-Lock / Identity-Preserving Pipeline (Missing Core Feature)
* **Loophole in TL Proposal:**
  * CraftAI Studio's primary flow (Web & Mobile) is **Selfie / Photo Remix** into Trending Templates.
  * `FLUX.1 Schnell` does **not** preserve facial identity, and OpenAI/Gemini often alter faces or reject likeness edits.
* **Fix (What to Tell TL):**
  * Add `"face_lock_remix"` as a first-class task type in `ai_models` and the Model Router.
  * When `face_reference_urls` is non-empty in `GenerationDispatchRequest`, route to a dedicated Face-Lock adapter (`fal-ai/flux-pulid` / `InstantID` via our `DiffusionStrategyFactory` upgrade), NOT plain `FLUX.1 Schnell`.

---

### Fix 3: Alternative to Forcing OpenRouter on Every Request
* **Loophole in TL Proposal:**
  * Calling OpenRouter on *every* prompt adds **1.5s–4s latency**, increases token cost, creates a **single point of failure**, and **corrupts curated Trending Template prompts** (which are already fine-tuned).
* **Alternative Solution (Conditional Intelligence Layer):**
  1. **Add `enhance_prompt: bool = False` flag:**
     * **Skip OpenRouter** when the user selects a curated Trending Template (`remixed_from_prompt_id` is set) or turns off Auto-Enhance.
     * **Use OpenRouter** only when `enhance_prompt=True`, when the user's prompt is very short/vague (`< 8` words with `model="auto"`), or for **Edit Intent parsing** (`preserve` / `modify` / `new_background`).
  2. **Strict Timeout + Bypass Fallback:**
     * Put a `2.5s` timeout on OpenRouter. If OpenRouter times out or returns 5xx, fall back to our existing fast `Groq`/`Gemini` client or pass the user's raw prompt directly—**never fail an image generation just because prompt enhancement failed.**

---

### Fix 4: Alternative to Playwright Inside FastAPI Container
* **Loophole in TL Proposal:**
  * Running headless Chromium via Playwright inside the FastAPI backend container bloats Docker images by **+1 GB**, consumes **500 MB–1 GB RAM per render** (causing OOM crashes), lacks system fonts by default, and introduces **SSRF / XSS security risks** if user HTML/URLs are rendered without sandboxing.
  * Additionally, blind `fit: "cover"` center-cropping cuts off people's heads in portrait templates.
* **Alternative Solutions:**
  * **Primary Recommendation (Lightweight Server + Client Canvas):**
    1. **Client-Side Interactive Preview:** Render template previews, text edits, and drag/crop adjustments directly in **Flutter (`CustomPainter` / `RepaintBoundary`)** and **Web (`HTML5 Canvas` / SVG)** for instant 60fps UX without hitting the server on every keystroke.
    2. **Server-Side Final Export via `Pillow + CairoSVG`:** For final high-res PNG/JPG/PDF export on the backend, use **Pillow + CairoSVG** (instead of Chromium). It uses **~20–40 MB RAM**, renders in **< 100 ms**, has zero browser SSRF surface, and bundles `.ttf` fonts cleanly.
    3. **Face-Aware Smart Crop:** Use our existing saliency/vision bounding-box logic before placing portraits into templates so heads/subjects are never sliced off.
  * **Secondary Option (Only if Complex CSS Flexbox/Grid Templates are Mandatory):**
    * Isolate Playwright into a **separate stateless worker container** (never inside the FastAPI API server) with outbound network blocked (`--disable-dev-shm-usage`, strict URL allowlist to block `169.254.169.254` / `file://`, and HTML escaping).

---

### Fix 5: Billing, Background Jobs & Storage Hardening
* **Loopholes in TL Proposal:**
  1. **Stuck Credit Reservations:** If a worker crashes mid-job, reserved credits remain locked forever.
  2. **No Creator Royalty Settlement:** TL's billing ignores `base_remix_fee` and `author_royalty_cut` from our `explore_prompts` remix economy.
  3. **No Webhook Signature Verification:** Spoofed callbacks to `/jobs/webhook` could inject fake URLs or trigger unearned refunds.
  4. **Raw 4K PNGs in Feeds:** Loading unoptimized multi-MB PNGs breaks mobile Explore/History scroll performance.
  5. **PG Queue Double-Pick:** Polling a Postgres job table without `FOR UPDATE SKIP LOCKED` causes duplicate provider calls.
* **Fixes:**
  * Add **`idempotency_key` (`UNIQUE (user_id, idempotency_key)`)** and **`reserved_until`** on generation jobs + a **Reaper Cron** to auto-refund stale `QUEUED`/`PROCESSING` jobs after 5 minutes.
  * Keep credit mutations atomic via PostgreSQL `SELECT ... FOR UPDATE` RPCs and retain our **Creator Royalty** split on template remixes.
  * Enforce cryptographic webhook verification (e.g., fal.ai Ed25519/JWKS signature check).
  * Stream provider downloads directly to Supabase Storage and generate a lightweight **WebP `preview_url`** alongside **`master_url`**.
  * Add **Supabase Realtime / FCM Push Notification** fallback for mobile when the app is backgrounded during 20s+ jobs.

---

### Fix 6: Existing Schema & Codebase Alignment (Only Adopt What's Genuinely Better)
Rather than breaking Web & Mobile by renaming tables or rewriting folders, we take a **clean additive migration** approach:
* **Adopt TL's genuinely useful new tables:** `ai_providers`, `ai_models`, `ai_usage_logs` (and `templates` / `compositions` when Phase 4 begins).
* **Keep our live tables & extend them:** Keep `wallets`, `wallet_ledger`, `generations`, `explore_prompts`, `artworks`, `remix_sessions` — just add missing columns (`provider_id`, `model_id`, `actual_cost`, `idempotency_key`, `parent_generation_id`, `version`) via Migration `010`.
* **Keep existing API routes:** Maintain `/api/v1/prompt-engineering/*` and root aliases in `app/api/v1/router.py`; add new endpoints (`/models`, `/compositions`) alongside them without breaking Web or Mobile.

---

## 3. ❌ What We Will NOT Adopt (And Why)

1. **Full Backend Folder Rewrite (`app/modules/...`):**
   * *Why:* `craftai_studio_backend` already has clean layering (`app/api/v1/endpoints/`, `app/services/`, `app/infrastructure/clients/`, `app/infrastructure/tools/`, `app/schemas/`). Moving everything to `app/modules/` adds zero user value and risks regressions across 10+ working routers. Instead, we implement `ImageProvider` + `ProviderRegistry` cleanly inside `app/infrastructure/clients/`.
2. **Replacing `wallets` with `user_credits` or `generations` with `generated_images`:**
   * *Why:* Our `wallets` table already handles `purchased_balance`, `earned_royalty_balance`, and atomic unlock/royalty ledgers, and both Web & Mobile query `generations` directly. Duplicating them would split user balances.
3. **Routing Basic Image Tools to Paid Gemini API:**
   * *Why:* We already have fast, zero-API-cost neural engines in `app/infrastructure/tools/` (`bg_remover_engine.py`, `lama_inpaint_service.py`, `upscaler_engine.py`, `ddcolor_service.py`). Background removal, upscaling, and colorization should stay on these dedicated tools instead of paying per-image Gemini API fees.

---

## 4. Unified Target JSON & Schema Specs (Ready to Adopt)

### A. Merged `image_models` Config JSON (For `ai_models` Table / `ConfigService`)
Combines TL's config-driven structure with our live validation & Face-Lock fixes:

```json
{
  "image_models": [
    {
      "id": "flux_schnell",
      "provider": "fal",
      "external_model_id": "fal-ai/flux/schnell",
      "tasks": ["text_to_image"],
      "tier": "economy",
      "credit_cost": 2.0,
      "supports_facelock": false,
      "supports_negative_prompt": false,
      "supports_transparency": false,
      "aspect_ratio_map": {
        "1:1": "square_hd",
        "16:9": "landscape_16_9",
        "9:16": "portrait_16_9",
        "4:5": "portrait_4_3"
      },
      "enabled": true
    },
    {
      "id": "flux_pulid_facelock",
      "provider": "fal",
      "external_model_id": "fal-ai/flux-pulid",
      "tasks": ["face_lock_remix"],
      "tier": "standard",
      "credit_cost": 3.0,
      "supports_facelock": true,
      "supports_negative_prompt": true,
      "supports_transparency": false,
      "enabled": true
    },
    {
      "id": "gpt_image_1",
      "provider": "openai",
      "external_model_id": "gpt-image-1",
      "tasks": ["text_to_image", "image_edit"],
      "tier": "premium",
      "credit_cost": 4.0,
      "supports_facelock": false,
      "supports_negative_prompt": false,
      "supports_transparency": true,
      "aspect_ratio_map": {
        "1:1": "1024x1024",
        "16:9": "1536x1024",
        "9:16": "1024x1536"
      },
      "enabled": true
    },
    {
      "id": "gemini_flash_image",
      "provider": "google",
      "external_model_id": "gemini-2.5-flash-image",
      "tasks": ["text_to_image", "image_edit"],
      "tier": "editing",
      "credit_cost": 3.0,
      "supports_facelock": false,
      "supports_negative_prompt": false,
      "supports_transparency": false,
      "enabled": true
    }
  ]
}
```

### B. Backward-Compatible Request Schema (`GenerationDispatchRequest` Extension)
Keeps all existing Web & Mobile fields intact while adding TL's routing & billing fields:

```json
{
  "task_id": "optional-client-uuid",
  "idempotency_key": "req_9f82a1c4",
  "prompt": "Cinematic neon street in neo-Tokyo...",
  "negative_prompt": "blurry, low quality",
  "model": "auto",
  "quality": "standard",
  "enhance_prompt": false,
  "aspect_ratio": "9:16",
  "face_reference_urls": ["https://.../user-selfie.jpg"],
  "anchor_image_url": "https://.../template-ref.jpg",
  "edit_instruction": null,
  "remixed_from_prompt_id": "10000000-0000-4000-8000-000000000001",
  "category": "Cyberpunk"
}
```

---

## 5. Summary Checklist to Share with TL

1. **Hybrid Gateway (`OpenRouter` + Direct Image APIs) & `ProviderRegistry`:** Agreed, we will implement this inside our existing `app/infrastructure/clients/` layer.
2. **Model IDs:** Need to replace `GPT Image 1.5` / `2.5` with verified live IDs (`gpt-image-1`, `fal-ai/flux/schnell`, `gemini-2.5-flash-image`) and strip `negative_prompt` on models that don't support it.
3. **Face-Lock Gap:** We must add a `face_lock_remix` route (`PuLID` / `InstantID`) because Selfie-to-Template remix is our core user flow.
4. **OpenRouter Alternative:** Don't force OpenRouter on every request—use `enhance_prompt: bool` so curated templates skip it (saving 2–4s latency and avoiding prompt drift) with a 2.5s timeout fallback.
5. **Playwright Alternative:** Avoid running headless Chromium inside FastAPI (high RAM + SSRF risk). Use Client Canvas preview + **Pillow + CairoSVG** for server export (or isolate Playwright into a separate sandboxed worker if complex HTML templates are strictly needed later).
6. **DB & Repo Alignment:** Keep live `wallets`, `generations`, `explore_prompts`, local `tools/`, and `/api/v1/*` routes intact; adopt `ai_providers`, `ai_models`, `ai_usage_logs`, and `idempotency_key` via an additive Migration `010`.
