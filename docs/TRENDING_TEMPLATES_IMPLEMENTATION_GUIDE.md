# Trending Images, Prompts & Template Remix Engine
## Production Implementation Guide for Mobile & Web Parity
**Version:** 1.0.0 (Production Master)  
**Target Systems:** Flutter (`craftai_studio_mobile`), Next.js (`craftai_studio_web`), FastAPI (`craftai_studio_backend`), Supabase PostgreSQL

---

## 1. Executive Summary & Architecture Overview

Modern generative AI platforms (ChatGPT, Google Gemini Imagen, Midjourney Explore) feature a dedicated **Trending Images & Inspiration Templates** showcase. In CraftAI Studio, this feature allows users to:
1. **Discover Curated & Community Trends:** Browse high-aesthetic, unmasked visual templates categorized across Cyberpunk, Photorealism, Product, 3D Render, Anime, Architecture, and Fantasy.
2. **Inspect Real Prompt Recipes:** View the full creative formula (positive prompt, negative prompt, model parameters, tags, and seed) rather than an obfuscated or encrypted stub.
3. **1-Tap Clipboard Copy:** Instantly copy the prompt recipe to the OS clipboard with tactile haptic feedback.
4. **Seamless Creation Handover (Zero Loopholes):**
   - **Use as Prompt:** Pre-loads the unmasked prompt recipe into the Studio prompt bar.
   - **Use as Ref:** Attaches the template image as a visual reference anchor.
   - **⚡ Remix on My Photo:** Allows the user to select their own gallery photo and applies the template's style with **Subject-Lock (Face-Lock)** constraints, retaining the user's facial likeness while styling the image.
   - **Creator Royalty Provenance:** Carries `remixedFromPromptId` so the original creator earns royalty cuts on every generated derivative.

### Zero-New-Backend-API Architecture
No additional microservice or FastAPI route is required. The mobile and web applications query Supabase's `explore_prompts` table directly using PostgREST client libraries, with high-speed indexes and instant fallback cache for offline resiliency.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Supabase PostgreSQL Database                       │
│                           (explore_prompts)                             │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
           ┌─────────────────────────┴─────────────────────────┐
           ▼                                                   ▼
┌───────────────────────┐                           ┌─────────────────────┐
│  craftai_studio_web   │                           │craftai_studio_mobile│
│(Next.js 14 App Router)│                           │  (Flutter / GetX)   │
├───────────────────────┤                           ├─────────────────────┤
│• Explore Grid (/explore)│                         │• ExploreDiscoveryView│
│• CardDetailModal      │                           │• ExploreCardWidget  │
│• 1-Tap Copy Prompt    │                           │• ImageDetailView    │
│• Handover to /studio  │                           │• Handover to Studio │
└───────────────────────┘                           └─────────────────────┘
```

---

## 2. Supabase SQL Schema Contract

The feature is anchored on Migration `009_trending_templates_and_prompts.sql` on the `explore_prompts` table. Both master setup scripts (`craftai_studio_backend/supabase/SUPABASE_SETUP_SQL_TO_RUN.sql` and `craftai_studio_mobile/SUPABASE_SETUP_SQL_TO_RUN.sql`) include this schema.

### Core Column Definitions

| Column Name | Type | Nullable | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | No | `gen_random_uuid()` | Unique prompt/template identifier |
| `title` | `TEXT` | No | `'Masterpiece'` | Display title of the template |
| `prompt` | `TEXT` | Yes | `NULL` | Full, unmasked creative recipe prompt |
| `negative_prompt` | `TEXT` | Yes | `'blurry, low quality...'` | Unwanted visual attributes |
| `category` | `TEXT` | No | `'Photorealism'` | Category (Cyberpunk, Anime, etc.) |
| `model_used` | `TEXT` | No | `'FLUX.1 Schnell'` | Primary AI diffusion model used |
| `aspect_ratio` | `VARCHAR(10)` | Yes | `'1:1'` | Aspect ratio (`1:1`, `16:9`, `9:16`, `4:5`) |
| `dimensions` | `VARCHAR(20)` | Yes | `'1024x1024'` | Canvas dimensions |
| `seed` | `BIGINT` | Yes | `42` | Random generation seed |
| `tags` | `TEXT[]` | Yes | `'{}'` | Array of search & topic tags |
| `preview_url` | `TEXT` | Yes | `NULL` | Image preview CDN URL |
| `preview_image_url`| `TEXT` | Yes | `NULL` | Alias for `preview_url` |
| `image_url` | `TEXT` | Yes | `NULL` | Alias for `preview_url` |
| `is_trending` | `BOOLEAN` | No | `TRUE` | Whether highlighted in Trending feed |
| `is_featured` | `BOOLEAN` | No | `TRUE` | Whether featured in top carousels |
| `display_order` | `INT` | No | `0` | Manual ordering weight (ASC) |
| `likes_count` | `INT` | No | `0` | Total community likes |
| `total_remixes` | `INT` | No | `0` | Total community remixes |
| `author_name` | `TEXT` | Yes | `'CraftAI Curated'` | Creator display name |
| `author_handle` | `TEXT` | Yes | `'@craftai'` | Creator handle |
| `author_avatar` | `TEXT` | Yes | `CDN URL` | Creator avatar URL |
| `base_remix_fee` | `NUMERIC(10,2)`| Yes | `4.00` | Credits charged to remix |
| `author_royalty_cut`| `NUMERIC(10,2)`| Yes | `1.60` | Royalty credits awarded to author |
| `is_marketplace_public`| `BOOLEAN` | No | `TRUE` | Row-Level Security visibility flag |

### Indexing & Performance
```sql
CREATE INDEX IF NOT EXISTS idx_explore_trending ON public.explore_prompts (is_trending, display_order ASC);
CREATE INDEX IF NOT EXISTS idx_explore_category_trending ON public.explore_prompts (category, is_trending, created_at DESC);
```

### Row Level Security (RLS) Policy
```sql
ALTER TABLE public.explore_prompts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public can view marketplace prompts" ON public.explore_prompts 
    FOR SELECT USING (is_marketplace_public = TRUE);

GRANT ALL ON public.explore_prompts TO anon, authenticated, service_role;
```

---

## 3. Mobile Model Deserialization (`ExploreCardModel`)

Located at: `lib/data/models/explore_card_model.dart`

### Key Mapping Rules to Prevent Loopholes:
1. **Dual URL Fallback:** Mobile must check `preview_image_url` -> `preview_url` -> `image_url` so images never break regardless of which backend alias is populated.
2. **Unmasked Prompt Fallback:** Mobile must check `full_prompt` -> `prompt` -> `masked_summary` -> `masked_prompt_summary`. If `prompt` exists in Supabase, it is stored in `fullPrompt` as the unmasked recipe.
3. **Array Parsing for Tags:** Safely map `json['tags']` to `List<String>`.
4. **Trending Flag:** Read `json['is_trending'] as bool? ?? false`.

```dart
factory ExploreCardModel.fromJson(Map<String, dynamic> json) {
  return ExploreCardModel(
    id: (json['id'] ?? '').toString(),
    authorName: json['author_name'] as String? ?? 'Creator',
    authorHandle: json['author_handle'] as String? ?? '@creator',
    authorAvatar: json['author_avatar'] as String? ??
        'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop',
    title: json['title'] as String? ?? 'Masterpiece',
    previewUrl: json['preview_image_url'] as String? ??
        json['preview_url'] as String? ??
        json['image_url'] as String? ??
        '',
    category: json['category'] as String? ?? 'General',
    maskedSummary: json['masked_summary'] as String? ??
        json['masked_prompt_summary'] as String? ??
        '',
    remixFee: (json['base_remix_fee'] as num?)?.toDouble() ??
        (json['remix_fee'] as num?)?.toDouble() ??
        4.0,
    creatorRoyaltyCut: (json['author_royalty_cut'] as num?)?.toDouble() ??
        (json['creator_royalty_cut'] as num?)?.toDouble() ??
        1.6,
    remixCount: (json['total_remixes'] as num?)?.toInt() ??
        (json['remix_count'] as num?)?.toInt() ??
        0,
    likeCount: (json['likes_count'] as num?)?.toInt() ??
        (json['like_count'] as num?)?.toInt() ??
        0,
    isLiked: json['is_liked'] as bool? ?? false,
    isBookmarked: json['is_bookmarked'] as bool? ?? false,
    modelUsed: json['model_used'] as String? ?? json['model'] as String? ?? 'FLUX.1 Schnell',
    toolApplied: json['tool_applied'] as String? ?? 'Text to Image',
    aspectRatio: json['aspect_ratio'] as String? ?? '1:1',
    dimensions: json['dimensions'] as String? ?? '1024x1024',
    seed: (json['seed'] as num?)?.toInt() ?? 42,
    costCredits: (json['cost_credits'] as num?)?.toDouble() ?? 2.0,
    fullPrompt: json['full_prompt'] as String? ??
        json['prompt'] as String? ??
        json['masked_summary'] as String? ??
        json['masked_prompt_summary'] as String?,
    negativePrompt: json['negative_prompt'] as String? ??
        'blurry, low quality, distorted, extra limbs, bad anatomy, text, watermark',
    createdAt: json['created_at'] != null
        ? json['created_at'].toString()
        : DateTime.now().toIso8601String(),
    tags: (json['tags'] as List?)?.map((e) => e.toString()).toList() ?? <String>[],
    isTrending: json['is_trending'] as bool? ?? false,
  );
}
```

---

## 4. UI Implementation Details

### A. Explore Feed Cards (`ExploreCardWidget.dart`)
- **Masonry Aspect Ratios:** Calculate scattered ratios dynamically (`index % 4` for organic visual rhythm: 0.80, 1.00, 0.75, 1.25).
- **Trending Badge:** When `card.isTrending == true`, render a sleek, high-contrast badge in the top-left corner:
  ```dart
  if (card.isTrending)
    Container(
      padding: EdgeInsets.symmetric(horizontal: 6.w, vertical: 3.h),
      decoration: BoxDecoration(
        color: AppColors.accentError.withValues(alpha: 0.85),
        borderRadius: BorderRadius.circular(AppDimens.radiusRound),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.local_fire_department, size: 10.sp, color: AppColors.white),
          SizedBox(width: 2.w),
          Text('Trending', style: AppTextStyles.captionXs.copyWith(color: AppColors.white, fontWeight: FontWeight.bold)),
        ],
      ),
    ),
  ```

### B. Prompt Inspection & 1-Tap Copy (`ExploreImageDetailView.dart`)
- **Full Prompt Display:** Display `widget.card.fullPrompt` with an expandable/collapsible toggle (`maxLines: _isPromptExpanded ? 20 : 3`).
- **1-Tap Clipboard Copy:**
  ```dart
  void _copyPromptToClipboard() {
    HapticFeedback.lightImpact();
    Clipboard.setData(ClipboardData(text: widget.card.fullPrompt));
    setState(() => _isCopied = true);

    Get.snackbar(
      'Prompt Copied! 📋',
      'The creative recipe has been copied to your clipboard.',
      snackPosition: SnackPosition.BOTTOM,
      backgroundColor: AppColors.surface,
      colorText: AppColors.primary,
      icon: Icon(Icons.check_circle_outline, color: AppColors.accentSuccess),
    );

    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) setState(() => _isCopied = false);
    });
  }
  ```

### C. Studio Handover (`StudioController.dart`)

Ensure all handovers use the unmasked prompt without the old `' • [Secret Recipe Encrypted]'` placeholder string:

```dart
// 1. Use as Prompt in Studio
void loadPromptFromRemix(ExploreCardModel card) {
  if (isBusy) return;
  remixedFromPromptId.value = card.id;
  final cleanPrompt = card.fullPrompt.isNotEmpty && !card.fullPrompt.contains('[Secret Recipe Encrypted]')
      ? card.fullPrompt
      : card.maskedSummary.replaceAll(' • [Secret Recipe Encrypted]', '');
  promptController.text = cleanPrompt;
}

// 2. ⚡ Remix on My Photo (Subject-Lock)
void remixOnMyPhoto(ExploreCardModel card, File userPhoto) {
  if (isBusy) return;
  remixedFromPromptId.value = card.id;
  referenceImages.clear();
  referenceImages.add(userPhoto.path);
  final cleanPrompt = card.fullPrompt.isNotEmpty && !card.fullPrompt.contains('[Secret Recipe Encrypted]')
      ? card.fullPrompt
      : card.maskedSummary.replaceAll(' • [Secret Recipe Encrypted]', '');
  promptController.text =
      'DO NOT CHANGE THE HUMAN SUBJECT. HUMAN SUBJECT — ABSOLUTE LOCK. $cleanPrompt';
}
```

---

## 5. Web Client Parity (`craftai_studio_web`)

The Web client implements exact functional parity with the mobile app:
- **Seed Artworks & Fallbacks:** Updated in `src/lib/supabase/db.ts` to include the same 12 unmasked prompt templates and tag definitions.
- **CardDetailModal:** Updated in `src/app/explore/page.tsx` with:
  - Unmasked Prompt Recipe box with 1-click clipboard copy + checkmark feedback.
  - Interactive `#tags` pills.
  - Collapsible Negative Prompt drawer.
  - Direct URL handover to `/studio?prompt=...&remixPromptId=...&imageUrl=...&faceLock=true`.
- **Trending Badges:** Displays glowing `Flame` badge on cards where `is_trending` is true.

---

## 6. Testing & Quality Assurance Checklist

| Checkpoint | Expected Behavior | Status |
| :--- | :--- | :--- |
| **Supabase Migration 009** | `explore_prompts` table contains all 12 curated templates with non-null `prompt`. | Verified |
| **Mobile Compilation** | `flutter analyze` runs clean with 0 warnings or errors. | Verified (0 issues) |
| **Web Type Safety** | `npx tsc --noEmit` passes with 0 type errors. | Verified |
| **Unmasked Prompt Display** | Card details display full creative text instead of `[Secret Recipe Encrypted]`. | Verified |
| **1-Tap Clipboard Copy** | Tapping "Copy Prompt" copies prompt text to clipboard and triggers haptic snackbar. | Verified |
| **Studio "Use as Prompt"** | Prompt bar in Studio fills with the template's creative prompt and sets creator attribution. | Verified |
| **Studio "⚡ Remix on My Photo"** | Prompts device gallery picker, attaches photo, and applies Subject-Lock prefix. | Verified |
| **Offline Fallback** | When network is unreachable, local seed templates render instantly without blank screens. | Verified |

