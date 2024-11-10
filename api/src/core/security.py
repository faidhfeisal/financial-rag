from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List, Dict
import jwt
from datetime import datetime, timedelta
import logging
from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Simple secret key for JWT - in production, use proper secret management
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = "HS256"

class Role:
    ADMIN = "admin"
    ANALYST = "analyst"
    USER = "user"

class Permission:
    READ_DOCUMENTS = "read:documents"
    WRITE_DOCUMENTS = "write:documents"
    DELETE_DOCUMENTS = "delete:documents"
    QUERY_SYSTEM = "query:system"

ROLE_PERMISSIONS = {
    Role.ADMIN: [
        Permission.READ_DOCUMENTS,
        Permission.WRITE_DOCUMENTS,
        Permission.DELETE_DOCUMENTS,
        Permission.QUERY_SYSTEM
    ],
    Role.ANALYST: [
        Permission.READ_DOCUMENTS,
        Permission.WRITE_DOCUMENTS,
        Permission.QUERY_SYSTEM
    ],
    Role.USER: [
        Permission.READ_DOCUMENTS,
        Permission.QUERY_SYSTEM
    ]
}

# Mock user store - In production, use a proper database
USERS = {
    "admin@example.com": {
        "id": "admin-1",
        "email": "admin@example.com",
        "password": "admin123",  # In production, use hashed passwords
        "role": Role.ADMIN
    },
    "analyst@example.com": {
        "id": "analyst-1",
        "email": "analyst@example.com",
        "password": "analyst123",
        "role": Role.ANALYST
    },
    "user@example.com": {
        "id": "user-1",
        "email": "user@example.com",
        "password": "user123",
        "role": Role.USER
    }
}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

class SecurityHandler(HTTPBearer):
    def __init__(self, required_permissions: Optional[List[str]] = None):
        super().__init__(auto_error=True)
        self.required_permissions = required_permissions or []

    async def __call__(self, request: Request) -> Dict:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        try:
            # Verify the token
            try:
                token_data = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            except jwt.ExpiredSignatureError:
                raise HTTPException(status_code=401, detail="Token has expired")
            except Exception as e:
                raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
            
            user_role = token_data.get("role", Role.USER)
            permissions = ROLE_PERMISSIONS.get(user_role, [])
            
            # Check required permissions
            if self.required_permissions:
                missing_permissions = set(self.required_permissions) - set(permissions)
                if missing_permissions:
                    raise HTTPException(
                        status_code=403,
                        detail="Not enough permissions"
                    )
            
            # Add user info to request state
            request.state.user = {
                "id": token_data["sub"],
                "email": token_data["email"],
                "role": user_role,
                "permissions": permissions
            }
            
            return request.state.user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise HTTPException(status_code=401, detail="Authentication failed")

def requires_auth(permissions: Optional[List[str]] = None):
    """Dependency for protected endpoints"""
    return SecurityHandler(required_permissions=permissions)