from typing import Optional
from fastapi import APIRouter, Header
from app.core.auth import invalidate_token
from app.core.supabase_client import get_supabase_admin
from app.core.logging import logger

router = APIRouter(tags=["Auth"])

@router.post("/auth/signout")
async def sign_out(authorization: Optional[str] = Header(None)):
    """
    Invalidates session token in server-side memory cache and terminates active session.
    Safe and idempotent — works for authenticated users and anonymous sessions without throwing errors.
    """
    token_invalidated = False
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split()[1]
        token_invalidated = invalidate_token(token)
        try:
            admin = get_supabase_admin()
            # Attempt admin session revocation if supported by client
            if hasattr(admin.auth, "admin") and hasattr(admin.auth.admin, "sign_out"):
                admin.auth.admin.sign_out(token)
            elif hasattr(admin.auth, "sign_out"):
                admin.auth.sign_out()
        except Exception as e:
            logger.debug(f"Notice on Supabase remote sign_out: {e}")

    logger.info(f"[Auth] Signout processed (token_invalidated={token_invalidated})")
    return {
        "status": "success",
        "message": "Signed out successfully",
        "cache_cleared": token_invalidated
    }
