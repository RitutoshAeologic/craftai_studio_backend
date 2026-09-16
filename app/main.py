from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import logger
from app.api.v1.router import api_v1_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="CraftAI Studio — FastAPI Enterprise Generative AI Gateway"
)

# Global CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enterprise Global Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_err = errors[0] if errors else {}
    loc = ' -> '.join([str(l) for l in first_err.get('loc', [])])
    msg = first_err.get('msg', 'Validation error')
    clean_msg = f"Invalid field '{loc}': {msg}" if loc else msg
    logger.warning(f"Validation error on {request.url.path}: {clean_msg}")
    return JSONResponse(
        status_code=422,
        content={
            'error': 'ValidationError',
            'message': clean_msg,
            'detail': errors,
            'details': errors
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(f"HTTPException {exc.status_code} on {request.url.path}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            'error': 'HTTPException',
            'message': str(exc.detail),
            'detail': exc.detail
        }
    )

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.warning(f"Handled AppException on {request.url.path}: {exc.message} (status {exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.critical(f"Unhandled Exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected server error occurred. Our engineering team has been notified."
        }
    )

# Master API v1 Router Registration
app.include_router(api_v1_router, prefix="/api/v1")

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "database": "Supabase PostgreSQL"
    }

@app.get("/api/v1/meta", tags=["Metadata"])
def api_metadata():
    return {
        "platform": "CraftAI Studio",
        "architecture": "Enterprise Clean Architecture (Routers -> DTOs -> Domain Services -> Infrastructure Clients)",
        "models_supported": ["flux_schnell", "sdxl", "instantid", "liveportrait"],
        "download_policy": "Flat 2 Credits Idempotent",
        "signed_url_ttl_seconds": 900
    }
