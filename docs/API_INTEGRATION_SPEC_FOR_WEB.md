# CraftAI Studio — Web Team API Integration Specification

> **Target Audience:** Next.js 15 Web Engineering Team  
> **Backend Architecture:** FastAPI (Python 3.9+) + Supabase (PostgreSQL, Storage, Auth)  
> **Backend Git Branch:** `feature/structured-prompt-engine` (Includes all gateway fixes + Multi-Model Structured Engine)  
> **Backend Repository:** `git@github.com:RitutoshAeologic/craftai_studio_backend.git`  
> **PR Link:** [Create PR on GitHub](https://github.com/RitutoshAeologic/craftai_studio_backend/pull/new/feature/structured-prompt-engine)  
> **Mobile Parity:** Flutter Mobile App (iOS / Android)  
> **Local Base URL (Recommended):** `http://127.0.0.1:8000/api/v1` *(or root `http://127.0.0.1:8000`)*  
> **Public HTTPS Tunnel (Remote Web Testing):** `https://craftwork-gizmo-engraved.ngrok-free.dev/api/v1` *(Header: `ngrok-skip-browser-warning: true`)*  
> **Swagger UI (Interactive Playground):** `http://127.0.0.1:8000/docs`  
> **ReDoc Documentation:** `http://127.0.0.1:8000/redoc`  
> **OpenAPI JSON Schema:** `http://127.0.0.1:8000/openapi.json`

---

## 1. Authentication & Security Headers

All requests from Next.js (Client Components or Server Actions) should pass the Supabase JWT access token obtained via `@supabase/ssr` / `@supabase/supabase-js`.

```http
Authorization: Bearer <SUPABASE_ACCESS_TOKEN>
Content-Type: application/json
```

---

## 2. Core Operational Endpoints (FastAPI)

### 2.1 Visual Generation Dispatch
- **Endpoint:** `POST /api/v1/prompt-engineering/generation/dispatch`
- **Description:** Dispatches a visual image generation task to serverless workers (FLUX.1-schnell or InstantID Face-Lock).

#### Request Payload:
```json
{
  "prompt": "An adorable 3D isometric diorama of a cyberpunk gaming room, miniature aesthetic, Octane Render lighting, 8k...",
  "character_id": null,
  "face_reference_urls": null,
  "negative_prompt": null,
  "structured_metadata": null,
  "width": 1024,
  "height": 1024,
  "seed": 42,
  "model": "flux",
  "remixed_from_prompt_id": null
}
```
*Field Notes:*
- `prompt` (string, 1–4000 characters): Supports rich master prompts.
- `negative_prompt` (string, optional): Explicit negative tokens to eliminate unwanted artifacts (used directly by SDXL / compiled engines).
- `structured_metadata` (object, optional): Visual Director metadata (`subject`, `environment`, `lighting`, `camera_optics`, `avoid`). When passed, the backend automatically compiles model-specific prompts for the target engine.
- `model` (string, optional): `"flux"` (default), `"gemini"`, or `"chatgpt"`.
- `width` / `height` (int, 512–2048): `1024x1024` (1:1), `768x1344` (9:16), `1344x768` (16:9).
- `face_reference_urls` (array of strings, optional): If 1–3 photo URLs are passed, engine auto-promotes to **Tier 1 (InstantID Face-Lock)**.
- `remixed_from_prompt_id` (string, optional): Pass original Explore card ID if user is remixing a community prompt for creator royalty split.

#### Response (HTTP 200):
```json
{
  "task_id": "gen_1dca6620",
  "tier": "Tier 0 (FLUX.1-schnell via Hugging Face)",
  "status": "ready",
  "estimated_seconds": 5,
  "direct_image_url": "https://txiuwtrmfvceddqsjvhk.supabase.co/storage/v1/object/public/user_generations/generations/flux_5681d376fa734038960f7d46fe96efaa.png"
}
```

---

### 2.2 Realtime Generation Progress (WebSocket & Polling)

#### A. WebSocket Progress Stream:
- **Endpoint:** `ws://127.0.0.1:8000/api/v1/prompt-engineering/generation/ws/generation/{task_id}`
- **Message format:**
```json
{
  "progress": 50,
  "status": "processing",
  "message": "Compiling diffusion prompt tokens..."
}
```

#### B. HTTP Polling Fallback (for disconnected clients):
- **Endpoint:** `GET /api/v1/prompt-engineering/status/{task_id}`
- **Response:**
```json
{
  "task_id": "gen_1dca6620",
  "status": "completed",
  "progress": 100,
  "output_url": "https://.../flux_output.png"
}
```

---

### 2.3 Dynamic Multi-LLM Configuration (Hot-Reloadable)
- **Endpoint:** `GET /api/v1/prompt-engineering/config`
- **Description:** Returns the active LLM provider, configured model mappings, fallback cascade order, and available providers.
- **Admin Hot-Reloading:** The active provider and models can be changed at runtime anytime by modifying the `llm_config` row in Supabase `app_settings` without restarting the server or redeploying code.

#### Response (HTTP 200):
```json
{
  "active_provider": "gemini",
  "fallback_order": ["gemini", "groq", "local"],
  "available_providers": ["gemini", "groq", "openai", "claude", "local"],
  "model_mappings": {
    "gemini": "gemini-2.5-flash",
    "groq": "qwen/qwen3.8-27b",
    "openai": "gpt-4o-mini",
    "claude": "claude-3-5-sonnet-20241022",
    "local": "offline-cinematic-engine"
  }
}
```

---

### 2.4 Prompt Engineering & Expansion (Magic Enhance)
- **Endpoint:** `POST /api/v1/prompt-engineering/expand`
- **Description:** Expands a short user idea into a 700+ character master prompt using the configured LLM with automatic failover cascade (Gemini 2.5 Flash -> Groq Qwen -> Local Offline Engine).
- **Character Limit:** `raw_prompt` supports up to **4,000 characters** (prevents 422 length truncation).
- **Option A Edit Preservation:** If `raw_prompt` contains `"Edit image1 as follows: "`, all LLM adapters preserve the exact prefix while expanding the descriptors.

#### Request:
```json
{
  "raw_prompt": "Makoto Shinkai aesthetic, golden hour clouds, floating islands",
  "starter_chip": "Cinematic",
  "aspect_ratio": "1:1",
  "ai_model": null
}
```
*Note:* Pass `ai_model: null` or omit to use the dynamic default from Supabase `app_settings`, or specify `"gemini"`, `"groq"`, `"openai"`, `"claude"`, or `"local"`.

#### Response (HTTP 200):
```json
{
  "master_prompt": "Breathtaking visual masterpiece in the distinctive anime aesthetic of Makoto Shinkai. Majestic floating islands drift suspended among radiant golden hour cumulonimbus clouds, bathed in amber sunlight, ultra-detailed 8K...",
  "negative_prompt": "blurry, low quality, distorted, extra limbs, watermark, signature",
  "complexity_score": 3,
  "model_used": "google/gemini-2.5-flash",
  "structured_metadata": {
    "subject": "Majestic floating islands suspended in the sky",
    "environment": "Radiant golden hour cumulonimbus clouds",
    "lighting": "Warm amber sunlight, atmospheric glow",
    "camera_optics": "35mm wide-angle, deep focus",
    "art_style": "Makoto Shinkai distinctive anime aesthetic",
    "avoid": ["blurry", "low quality", "distorted", "watermark"],
    "preserved_elements": []
  }
}
```

#### 2.4.1 Multi-Model Structured Prompt Engine (Web Implementation Guide)

The prompt expansion engine now returns both the synthesized **`master_prompt`** and a detailed **`structured_metadata`** object (Visual Director breakdown).

##### A. TypeScript Interfaces for Web:
```typescript
export interface StructuredPromptMetadata {
  subject: string;             // Central character/entity description
  environment: string;         // Background, atmospheric setting
  lighting: string;            // Cinematic lighting, rim lights, shadow dynamics
  camera_optics: string;       // Lens focal length, aperture (e.g. f/1.4), film grain
  art_style: string;           // Overall artistic genre or rendering engine
  avoid: string[];             // Negative visual concepts to suppress
  preserved_elements: string[];// Identity features, faces, or elements locked from modification
}

export interface PromptExpandResponse {
  master_prompt: string;
  negative_prompt: string;
  complexity_score: number;
  model_used: string;
  structured_metadata?: StructuredPromptMetadata;
}
```

##### B. How the Next.js Web UI Should Utilize This:
1. **Interactive Prompt Inspector (Studio UI Parity):**
   - In Studio, clicking the Inspector icon (`Icons.manage_search`) opens a modal displaying:
     - **What You Typed:** The user's clean draft.
     - **AI Visual Breakdown:** Visual director badges for `Subject`, `Environment`, `Lighting`, `Camera Optics`, `Style`.
     - **Preserved Identity Badges:** Green locked pills for anything in `preserved_elements` (e.g., `🔒 Authentic Facial Structure Locked`).
2. **Passing to Generation Dispatch (`/generation/dispatch`):**
   - Forward `structured_metadata` in the POST body to `/generation/dispatch`.
   - The backend's `PromptCompiler` automatically compiles model-specific prompts:
     - **FLUX.1-schnell:** Compiles into a rich natural-language visual narrative (ideal for FLUX text encoders).
     - **SDXL:** Compiles into weighted bracketed tags (`(35mm film grain:1.2), ...`).
3. **Identity & Facial Preservation:**
   - When users enter prompts like *"1985 Bollywood style and keep my face preserved"*, the LLM extracts the identity traits into `preserved_elements`.
   - The Conversational Chat Copilot (`/chat-delta`) locks these elements, preventing subsequent refinement turns from altering facial features.

---

### 2.5 Prompt Chat Copilot (Delta Compiler)
- **Endpoint:** `POST /api/v1/prompt-engineering/chat-delta`
- **Description:** Conversational prompt refiner for natural language tweaks (e.g., *"Make it nighttime and add neon rain"*). Preserves `"Edit image1 as follows: "` during image-to-image refinement. Updates structured metadata while locking preserved elements.

#### Request:
```json
{
  "base_prompt": "Edit image1 as follows: white tiger",
  "user_instruction": "add glowing blue eyes and royal gold crown",
  "session_id": "copilot-sess-456",
  "turn_count": 1,
  "ai_model": null
}
```
*Note:* `session_id` is **optional** (backend auto-generates a unique `sess_<id>` if omitted, preventing 422 errors). `turn_count` defaults to `1`. `ai_model` defaults to active Supabase config.

#### Response (HTTP 200):
```json
{
  "compiled_prompt": "Edit image1 as follows: white tiger with glowing blue eyes, ornate 24k gold crown, cinematic lighting, photorealistic textures",
  "diff": {
    "added": ["with glowing blue eyes", "ornate 24k gold crown"],
    "removed": []
  },
  "suggested_chips": ["Add Rim Light", "35mm Grain", "Bokeh Background"],
  "model_used": "google/gemini-2.5-flash",
  "structured_metadata": {
    "subject": "white tiger with glowing blue eyes, ornate 24k gold crown",
    "environment": "seamless studio background",
    "lighting": "cinematic lighting, rim reflections",
    "camera_optics": "85mm portrait lens, f/1.4",
    "art_style": "photorealistic textures",
    "avoid": ["blurry", "distorted"],
    "preserved_elements": ["white tiger"]
  }
}
```

---

### 2.5 Creative Skills Toolbox (Quick Tools)

#### A. AI Background Remover:
- **Endpoint:** `POST /api/v1/prompt-engineering/tools/remove-background`
- **Request:** (Supports both HTTPS URL and Base64 Data URL)
```json
{
  "image_url": "https://.../photo.png"
}
```
- **Response:** (Returns both `output_url` and `cutout_url` with identical values)
```json
{
  "task_id": "tool_rmbg_abc123",
  "status": "completed",
  "output_url": "https://.../photo_transparent.png",
  "cutout_url": "https://.../photo_transparent.png"
}
```

#### B. Tool Presets (Relight, Blur, Upscale):
- **Endpoint:** `POST /api/v1/prompt-engineering/tools/edit-preset`
- **Request:** (`image_url` is optional; if omitted, backend looks up `image_id` in `jobs` table)
```json
{
  "image_id": "job_123",
  "image_url": "https://.../photo.png (optional - URL or base64)",
  "action": "relight",
  "target_preset": "golden_hour",
  "lock_subject": true
}
```
- **Response:** (Returns both `output_url` and `image_url`)
```json
{
  "task_id": "tool_job_123_abc",
  "status": "completed",
  "applied_tool": "relight",
  "subject_masked": true,
  "tokens_consumed": 0,
  "output_url": "https://.../transformed.png",
  "image_url": "https://.../transformed.png"
}
```

---

### 2.6 Multimodal Aesthetic Vision Scanner
- **Endpoint:** `POST /api/v1/vision-scan` *(or `/api/v1/prompt-engineering/vision-scan`)*
- **Description:** Reverse-engineers aesthetic concepts, style tags, and camera optics from a reference image using Gemini 2.5 Flash.
- **Request:** (Accepts JSON request body or URL query parameter `?photo_url=...`)
```json
{
  "image_url": "https://.../reference_photo.png"
}
```
- **Response (HTTP 200):**
```json
{
  "extracted_prompt": "Close-up, natural light portrait of a beautiful young woman...",
  "detected_style": "Natural Light Portraiture",
  "lighting_optics": "Natural golden hour light, 85mm f/1.8",
  "model_used": "google/gemini-2.5-flash (Live AI)"
}
```

---

### 2.7 Ephemeral Face-Lock Reference Photos
- **Upload Endpoint:** `POST /api/v1/prompt-engineering/upload-reference` (Multipart form-data: `file`)
- **Cleanup Endpoint:** `POST /api/v1/prompt-engineering/cleanup-reference` (JSON: `{"image_url": "https://..."}`)
- *Note:* Backend auto-purges reference photos 30 seconds after generation to enforce the **Zero-Retention Privacy Policy**.

---

### 2.8 System Health Verification
- **Endpoints:** `GET /health` and `GET /api/v1/health`
- **Response (HTTP 200):**
```json
{
  "status": "healthy",
  "service": "CraftAI Studio Backend",
  "version": "1.0.0"
}
```

---

### 2.9 Standardized API Error Response Contract
FastAPI has been enhanced with unified global exception handlers. All errors consistently return JSON formatted for seamless frontend consumption:

#### A. Pydantic Validation Error (HTTP 422):
Returned when a request body fails schema constraints. Includes a clear, human-readable summary in `message`:
```json
{
  "error": "ValidationError",
  "message": "Invalid field 'body -> raw_prompt': String should have at least 1 character",
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "raw_prompt"],
      "msg": "String should have at least 1 character"
    }
  ],
  "details": [...]
}
```

#### B. Domain / Application Exception (HTTP 400, 429, 504):
Returned for rate limits, safety moderation blocks, or provider timeouts:
```json
{
  "error": "RateLimitException",
  "message": "Rate limit reached. Please generate or wait before next refine.",
  "details": { "retry_after": 60 }
}
```

#### C. Unhandled Server Error (HTTP 500):
Returned for unforeseen backend exceptions; logs traceback server-side and shields internal infrastructure:
```json
{
  "error": "InternalServerError",
  "message": "An unexpected server error occurred. Our engineering team has been notified."
}
```

> **Web Implementation Tip (Axios / Fetch):**  
> Always read `err.response?.data?.message || err.response?.data?.detail?.[0]?.msg || err.message` to display user-friendly toast alerts.

---

## 3. Supabase Direct Database Schemas

The Web app can read and write directly to Supabase via `@supabase/ssr` / `@supabase/supabase-js`. Row Level Security (RLS) policies are active.

### 3.1 `jobs` Table (User Generations)
| Column | Type | Description |
| :--- | :--- | :--- |
| `job_id` | `TEXT PRIMARY KEY` | Unique task ID (e.g. `gen_1dca6620`) |
| `user_id` | `UUID REFERENCES auth.users` | Creation author |
| `type` | `TEXT` | `'IMAGE_GEN'`, `'TOOL_BG'`, etc. |
| `status` | `TEXT` | `'completed'`, `'failed'`, `'processing'` |
| `prompt` | `TEXT` | **Clean User Display Prompt** (Anti-Theft protected) |
| `preview_url` | `TEXT` | Output preview URL in Supabase Storage |
| `credits_deducted` | `NUMERIC(6,2)` | Generation fee charged (e.g., `2.00`) |
| `is_download_unlocked` | `BOOLEAN` | `false` initially; `true` once 2-credit paywall is unlocked |

### 3.2 `wallets` Table (Credits Ledger)
| Column | Type | Description |
| :--- | :--- | :--- |
| `user_id` | `UUID PRIMARY KEY` | User ID |
| `credits` | `NUMERIC(10,2)` | Total usable credits balance |
| `purchased_balance` | `NUMERIC(10,2)` | Credits bought via Stripe (qualifies for creator royalties) |
| `earned_royalty_balance` | `NUMERIC(10,2)` | Accrued earnings from community prompt remixes |

### 3.3 `explore_prompts` Table (Community Feed)
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID PRIMARY KEY` | Card ID |
| `author_id` | `UUID REFERENCES auth.users` | Creator |
| `title` | `TEXT` | Short title (e.g., `"Cyber Ronin in Rain"`) |
| `preview_url` | `TEXT` | High-res visual preview |
| `category` | `TEXT` | `'Cyberpunk'`, `'Anime'`, `'Photorealism'`, etc. |
| `masked_summary` | `TEXT` | **Public style tags only** (e.g., `"Cyber Ronin • Wet Neon • 85mm"`) |
| `remix_fee` | `NUMERIC(4,1)` | Remix cost (e.g., `4.0`) |
| `creator_royalty_cut` | `NUMERIC(4,1)` | Author royalty share (e.g., `1.6` = 40%) |
| `remix_count` | `INTEGER` | Community remixes counter |
| `like_count` | `INTEGER` | Likes counter |

---

## 4. Crucial Business Rules (Match Flutter Flow)

1. **Rule 1: Download Paywall Gate (2 Credits)**
   - Cloud Library shows creations for free.
   - Tapping "Download 4K Master" opens the 2-Credit Paywall modal.
   - Check `job.is_download_unlocked`:
     - If `true`: Re-download is **100% Free** (Idempotent).
     - If `false`: Deduct 2 Credits from wallet, update `is_download_unlocked = true`, and trigger lossless download.

2. **Rule 2: Creator Royalty on Remix**
   - In Explore feed, tapping "Use as Prompt" loads `masked_summary` into the Studio input, and attaches `remixed_from_prompt_id = card.id`.
   - On generation, pass `remixed_from_prompt_id` to `/generation/dispatch` so the backend credits the author their royalty split.

3. **Rule 4: Secret Formula DRM & Anti-Theft**
   - **Never** render or send the raw 700+ character master prompt to public Explore cards or unauthenticated web inspectors.
   - Public cards and previews only expose `masked_summary`.
   - In Studio, the user sees their clean prompt in the input box, while the Gemini-expanded master recipe is dispatched to FLUX under the hood.

---

## 5. Complete Frontend UI & User Flow Parity Guide (Mobile ↔ Web)

The Web application must reflect the **exact same UI structure, screens, user flows, and state behaviors** as the Flutter mobile app.

### 5.1 Design System & Theme Tokens
| Token Name | Hex Code | Purpose |
| :--- | :--- | :--- |
| `AppColors.primary` | `#6366F1` (Indigo) | Primary buttons, active tabs, magic enhance highlights |
| `AppColors.primaryDark` | `#4F46E5` | Hover/Pressed states on primary buttons |
| `AppColors.surface` | `#121218` | Main card backgrounds, modal sheets, studio canvas |
| `AppColors.surfaceLight` | `#1E1E2A` | Input fields, secondary cards, pill badges |
| `AppColors.background` | `#0B0B0F` | Deep dark page background |
| `AppColors.border` | `#2E2E3E` | Card borders, dividers, outlines |
| `AppColors.textPrimary` | `#FFFFFF` | Main headings, active inputs |
| `AppColors.textSecondary` | `#94A3B8` | Subtitles, helper text, inactive chips |
| `AppColors.textMuted` | `#64748B` | Timestamps, counters, placeholder text |
| `AppColors.accentSuccess` | `#10B981` | Unlocked downloads, face-lock active, credits refund |
| `AppColors.accentWarning` | `#F59E0B` | Low credits warning, disarmed status |
| `AppColors.accentError` | `#EF4444` | Server error sheets, validation errors, liked heart |
| `AppColors.copilotAccent` | `#38BDF8` (Sky Blue) | Prompt Chat Copilot icon and badges |
| `AppColors.purpleAccent` | `#A855F7` (Purple) | Subject Lock action icon and badges |

---

### 5.2 Screen 1: Explore Community Feed (`/explore`)
- **Layout:** Masonry grid (Pinterest-style) with category tabs at the top (`All`, `Cyberpunk`, `Photorealism`, `Anime`, `Product`, `Character`, `Architecture`, `3D Render`).
- **Feed Card Elements:**
  - Full-bleed image preview.
  - Category pill in top-left corner.
  - Like heart button & counter in top-right corner.
  - Bottom info: Author avatar, author name/handle, remix counter.
- **Card Detail Drawer / Modal (On Card Click):**
  - High-res image display with like action.
  - Author profile info and **Creator Royalty Badge** (e.g., `40% Royalty`).
  - **Prompt Recipe Box:** Displays `card.masked_summary` (e.g., `"Cyber Ronin • Wet Neon Street • 85mm Bokeh • [Secret Recipe Encrypted]"`).
  - **Dual Action Buttons:**
    1. **`Use as Prompt`**: Copies `masked_summary` to Studio prompt input, records `remixed_from_prompt_id = card.id`, and routes to `/studio`.
    2. **`Use as Ref`**: Injects card's image into Studio reference image slot, and routes to `/studio`.
    3. **`⚡ Remix on My Photo`**: Prompts user to upload a selfie/photo, sets Subject-Lock, and routes to Studio.

---

### 5.3 Screen 2: AI Creation Studio (`/studio`)
- **Consistent Character / Face Lock Bar (Top):**
  - Profile selector with 3-angle face reference chips (Front, 45°, Profile).
  - When selected, automatically activates **InstantID Face-Lock (Tier 1)**.
- **Multi-Reference Photo Slots (`+ Add reference images`):**
  - Up to 3 reference photo chips for style/pose transfer.
- **Interactive Prompt Box:**
  - **Engine Selector Chip:** Dropdown allowing user to select between Gemini 2.5 Flash, Groq Llama 3.3, Claude 3.5 Sonnet.
  - **Prompt Textarea:** Clean user prompt draft with live character counter.
  - **Action Toolbar (Bottom Right of Box):**
    - `Icons.chat_bubble_outline` → Opens **Prompt Chat Copilot** drawer for conversational prompt tweaks.
    - `Icons.copy_rounded` → Copies the prompt text to clipboard.
    - `Icons.manage_search_rounded` → Opens **Prompt Lifecycle Inspector** modal (What you typed vs Gemini refined vs Sent to FLUX).
    - **`✨ Enhance` Button:** Calls `/api/v1/prompt-engineering/expand`.
- **Option A: "AI Master Formula Armed" Indicator:**
  - When enhanced, the input box keeps the user's clean prompt, while a sleek pill badge appears underneath:
    `✨ AI Master Formula Armed • Ready for FLUX generation [✕]`
  - Clicking `[✕]` disarms the enhancement and reverts to raw prompt mode.
- **Studio Controls Bar:**
  - **Aspect Ratio Selector:** `Auto`, `1:1` (Square), `9:16` (Story/Reel), `16:9` (Widescreen), `4:5` (Portrait).
  - **Model Selector:** `FLUX.1-schnell`, `Gemini Imagen 3`, `ChatGPT DALL-E 3`.
  - **Dynamic Credit Generate Button:** Displays calculated cost (e.g., `Generate ✨ 2 Cr`).
- **Robust Loading Lifecycle & Task Lockdown (Web Parity):**
  - **Task Mutual Exclusion (`isBusy`):**
    - While generation (`isGenerating`), prompt enhance (`isEnhancing`), or background removal is running, all creative configuration inputs (prompt textarea, template chips, reference photo slots, face-lock bar, model pills) are **locked & dimmed (opacity 0.6)**.
    - Secondary task actions are blocked to prevent duplicate credit deduction or concurrency race conditions.
  - **Live Generation Progress Card:**
    - Live progress bar (0% to 100%) showing real-time phase updates from WebSocket (e.g., *"Preparing creative canvas..."*, *"Compiling diffusion latents..."*, *"FLUX.1-schnell denoising 1024x1024 latents..."*, *"✨ Masterpiece ready! Opening Library..."*).
    - Status pill indicates: `Studio locked • Diffusion process in progress`.
  - **Clean Loading Reset:**
    - On success: progress bar hits 100%, displays brief completion confirmation (400ms), and then **resets progress to 0% and phase to empty** before routing to `/library`.
    - On failure (422, 500, network, timeout): loading states **immediately reset to 0%**, credits are auto-refunded, and a clean, user-friendly error sheet displays with plain-language explanations (no raw traceback) and a 1-tap `Retry` button.

---

### 5.4 Screen 3: Cloud Library & Paywall Gate (`/library`)
- **Layout:** Grid/List of the user's personal creations (`myCreations`).
- **Creation Card:**
  - Image preview.
  - User's clean prompt text.
  - Status pill:
    - `Cloud Saved (Free)`: Image is saved in personal cloud storage.
    - `Unlocked (4K Ready)`: Image has been unlocked for lossless 4K export.
  - **Action Button:**
    - If unlocked: **`Re-Download (Free $0.00)`**.
    - If locked: **`Download 4K (2 Cr)`** → Launches **Download Paywall Modal**.
- **Download Paywall Modal:**
  - Displays: Lossless 4K Master Export badge, explanation of 2 Credits ($0.20) fee, and idempotent re-download guarantee.
  - **`Confirm & Unlock (2 Credits)`** button: Deducts 2 Credits from wallet, updates `jobs.is_download_unlocked = true`, and downloads lossless PNG.

#### 5.4.1 MeiGen Creation Detail View (`/library/[jobId]`)
Clicking any creation card in the Library (or Explore feed) opens the **Creation Detail View**:
- **Top Navigation Bar:**
  - Back button (`<`) on top-left.
  - **`+ Publish`** button on top-right: Allows author to publish their creation to the public Explore community feed with creator remix royalties.
- **Hero Image Viewer:** Full-bleed, high-resolution preview with zoom/pan.
- **Actions Row:**
  - Heart / Like toggle button with live count.
  - Download icon (triggers 4K paywall or direct export).
  - Copy prompt button (`📋 Copy`).
  - Three-dot overflow menu (`⋮`).
- **Creator Attribution:** Avatar, author username/handle, creation timestamp.
- **Prompt Description:** Clean user prompt text with expandable `More` / `Less` toggle.
- **Floating Bottom Pill Button:**
  - **`✏️ Edit image`**: Floating bottom action button (rounded pill, high contrast) that triggers the **Edit Actions Sheet**.

#### 5.4.2 Edit Actions Sheet (MeiGen 5-Action Modal)
Triggered by tapping `✏️ Edit image`:
1. **`✨ Describe edits`**:
   - Routes to `/studio`.
   - Injects the selected image into reference slot **`image1`** with remove (`✕`) and add (`+`) controls.
   - Pre-fills the prompt textarea with **`"Edit image1 as follows: "`**.
   - Displays the **`[AI Edit]`** badge in the prompt toolbar.
2. **`✂️ Remove Background`**:
   - Routes to `/tools` with the image pre-loaded into the Zero-Token CPU Background Remover tool.
3. **`🔄 Use prompt`**:
   - Routes to `/studio` with the raw prompt loaded into the textarea (without image attachment).
4. **`🎬 Make Video`**:
   - Routes to Image-to-Video generation tool.
5. **`4K+ Upscale 4K`**:
   - Opens the Lossless 4K Master Export paywall modal.
6. **`Cancel` Button**: Dismisses modal.

---

### 5.5 Screen 4: Wallet & Top-Up (`/wallet`)
- **Balance Card:**
  - Total Credits available.
  - Breakdown: `Purchased Credits` (qualifies for creator remix royalties) vs `Earned Royalty Balance` (creator earnings).
- **Top-Up Packages:**
  - Starter: 50 Credits ($4.99)
  - Pro Creator: 200 Credits ($14.99)
  - Studio Master: 500 Credits ($29.99)
- **Stripe Checkout Webhook:**
  - Handled via `POST /api/v1/wallet/stripe-webhook` which credits `wallets.purchased_balance`.
- **Transaction History:**
  - List of recent credit debits (generations, downloads) and credits (purchases, remix royalties).

---

### 5.6 Screen 5: Creative Skills Toolbox (`/tools`)
- **Background Remover:** Upload image or select from library → 1-tap transparent PNG cutout preview with before/after slider.
- **Portrait Relighting & Depth Bokeh:** Adjust studio lighting presets (Golden hour, Studio neon, Rim light).
- **4K Lossless Upscaler:** Detail synthesis and super-resolution upscaler.
