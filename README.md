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
uvicorn app.main:app --reload --port 8001
```

## Architecture: Abstract Interfaces & Dependency Injection

The backend is strictly architected using **clean architecture**, **abstract interfaces**, and **FastAPI dependency injection (`Depends`)**. This allows seamless swapping of API keys, models, and providers without modifying core application business logic.

### 1. Abstract Base Interfaces (`app/infrastructure/clients/base.py`)
All LLM and Diffusion clients implement unified abstract base contracts:
- **`ILLMClient`**: Enforces standardized signatures across all conversational LLM providers:
  - `expand_prompt(raw_prompt: str, starter_chip: Optional[str]) -> Dict[str, Any]`
  - `compile_delta(base_prompt: str, user_instruction: str) -> Dict[str, Any]`
  Implemented by: `GeminiLLMClient`, `OpenAILLMClient`, `GroqLLMClient`, `ClaudeLLMClient`, `LocalOfflineLLMClient` (Ollama Qwen 3.5 9B / Qwen 2.5 7B).
- **`IDiffusionGateway`**: Enforces standardized signatures for text-to-image and image-to-image editing:
  - `generate_image(...) -> Optional[bytes]`
  - `edit_image(...) -> Optional[bytes]`
  Implemented by: `CloudflareAIClient` (FLUX.1-schnell), `LocalDiffusionClient` (FLUX.2 [klein] 4B / SDXL-Turbo on Apple Silicon Metal GPU), `PollinationsGateway`, and `HuggingFaceClient`.

### 2. Centralized Configuration & Key Swapping (`app/core/config.py`)
- All provider API keys, base URLs, and active model names are centralized in `app.core.config.Settings` and driven exclusively by `.env`.
- To switch a model name or API key (e.g. `GEMINI_API_KEY`, `OPENAI_API_KEY`, `CLOUDFLARE_IMAGE_MODEL`, or `OLLAMA_MODEL`), simply update the `.env` value or pass the new identifier into the client constructor. No downstream endpoints, routers, or schemas need changes.

### 3. Pluggable Dependency Injection (`app/api/deps.py`)
- FastAPI injectors (`get_prompt_service`, `get_generation_service`, `get_llm_client`, `get_diffusion_gateway`) wire interfaces directly to the business layer.
- Changing or adding a fallback provider simply requires updating the injected factory in `deps.py`.

