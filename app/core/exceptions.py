from typing import Optional, Dict, Any

class AppException(Exception):
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class ProviderTimeoutException(AppException):
    def __init__(self, provider: str, message: str = "Provider upstream timeout. Circuit breaker initiated."):
        super().__init__(message=message, status_code=504, details={"provider": provider})

class RateLimitException(AppException):
    def __init__(self, message: str = "Rate limit reached. Please generate or wait before next refine.", retry_after: int = 60):
        super().__init__(message=message, status_code=429, details={"retry_after": retry_after})

class ValidationException(AppException):
    def __init__(self, message: str, field_errors: Optional[Dict[str, str]] = None):
        super().__init__(message=message, status_code=400, details={"field_errors": field_errors or {}})

class ModerationException(AppException):
    def __init__(self, reason: str = "Content flagged by safety policy"):
        super().__init__(message=f"Prompt blocked by moderation filter: {reason}", status_code=422, details={"reason": reason})

class ResourceNotFoundException(AppException):
    def __init__(self, resource: str, identifier: str):
        super().__init__(message=f"{resource} '{identifier}' not found.", status_code=404, details={"resource": resource, "id": identifier})
