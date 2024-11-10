from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import timedelta
from ...core.security import (
    USERS,
    create_access_token,
    requires_auth,
    Role
)

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    expires_in: int

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Login endpoint"""
    user = USERS.get(request.email)
    if not user or user["password"] != request.password:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )

    # Create access token
    token_data = {
        "sub": user["id"],
        "email": user["email"],
        "role": user["role"]
    }
    expires = timedelta(hours=8)
    token = create_access_token(token_data, expires)

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "expires_in": int(expires.total_seconds())
    }

@router.get("/me")
async def get_current_user(user=Depends(requires_auth())):
    """Get current user info"""
    return user