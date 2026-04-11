from pydantic import BaseModel, Field, EmailStr
from typing import Optional

class RegisterBody(BaseModel):
    username: str = Field(..., min_length=5, max_length=50, pattern=r"^[a-zA-Z0-9_@#]+$")
    email: EmailStr
    password: str
    password_confirm: str
    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "johndoe",
                "email": "john@example.com",
                "password": "Secure@123",
                "password_confirm": "Secure@123"
            }
        }
    }

class VerifyOTPBody(BaseModel):
    email: str
    otp: str
    model_config = {
        "json_schema_extra": {
            "example": {"email": "john@example.com", "otp": "482910"}
        }
    }

class LoginBody(BaseModel):
    identifier: str
    password: str
    model_config = {
        "json_schema_extra": {
            "example": {"identifier": "john@example.com", "password": "Secure@123"}
        }
    }

class PasswordResetRequestBody(BaseModel):
    email: str
    model_config = {
        "json_schema_extra": {"example": {"email": "john@example.com"}}
    }

class PasswordResetVerifyBody(BaseModel):
    email: str
    otp: str
    model_config = {
        "json_schema_extra": {
            "example": {"email": "john@example.com", "otp": "837201"}
        }
    }

class PasswordResetConfirmBody(BaseModel):
    email: str
    reset_token: str
    new_password: str
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "john@example.com",
                "reset_token": "a3f1c9d8...",
                "new_password": "NewSecure@456"
            }
        }
    }

class RefreshBody(BaseModel):
    refresh_token: str
    model_config = {
        "json_schema_extra": {
            "example": {"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
        }
    }

class ResendOTPBody(BaseModel):
    email: str
    model_config = {
        "json_schema_extra": {"example": {"email": "john@example.com"}}
    }

class ProfileUpdateBody(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100, description="User's display name")
    username: Optional[str] = Field(None, min_length=5, max_length=50, description="New username (must be unique)")
    model_config = {
        "json_schema_extra": {
            "example": {
                "display_name": "John Doe",
                "username": "johndoe_new"
            }
        }
    }

class UserOut(BaseModel):
    id: str
    username: str
    display_name: Optional[str] = None
    email: str
    profile_image_url: Optional[str] = None
    api_key: Optional[str] = None
    is_active: bool
    created_at: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    user: Optional[UserOut] = None

class MessageResponse(BaseModel):
    message: str
    email: Optional[str] = None

class ResetTokenResponse(BaseModel):
    reset_token: str
    message: str

class ErrorResponse(BaseModel):
    status: str = "error"
    error: str
    status_code: int
    detail: Optional[object] = None