# CraftAI Studio — FastAPI & Supabase Backend

Compute gateway, prompt DRM encryptor, complexity pricing analyzer, and queue orchestrator.

## Tech Stack
- **API Framework:** FastAPI (Python 3.11)
- **Database & Storage:** Supabase (PostgreSQL 15+, `pgvector`, Row Level Security, S3-Compatible Storage)
- **AI Integrations:** Google Gemini 1.5 Flash (Magic Prompt Expansion & Vision), Serverless GPU Inference (RunPod / Modal / T4)
- **Payments:** Stripe Webhook fulfillment (`POST /api/v1/wallet/stripe-webhook`)

## Key Modules
1. **Dynamic Token Complexity Analyzer:** Range-bound credit calculation with `round_half_up` rounding.
2. **Server-Side AES-256 Prompt DRM:** Secret recipes encrypted with AES-256-GCM; client sees masked abstracts only.
3. **Anti-Sybil Royalty Ledger:** Creator remix royalties strictly funded from `purchased_balance`.
4. **Idempotent 4K Downloads:** Supabase Storage Signed URLs with 15-minute (900s) TTL, re-downloads are free.
5. **Semantic Discovery:** PostgreSQL `pgvector` powering "More like this" recommendations.

## Quick Start
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
