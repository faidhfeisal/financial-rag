from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ...core.config import get_settings

settings = get_settings()

class AuthMiddleware(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        if not credentials:
            raise HTTPException(
                status_code=403,
                detail="Invalid authorization credentials"
            )
            
        # In production, implement proper token validation
        # This is just a placeholder
        if credentials.credentials != "your-secret-token":
            raise HTTPException(
                status_code=403,
                detail="Invalid token or expired token"
            )
            
        return credentials.credentials