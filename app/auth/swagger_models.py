"""
Pydantic models for Swagger / OpenAPI documentation.

Used by flask-openapi3 to auto-generate the OpenAPI spec and Swagger UI.
Marshmallow schemas in schemas.py remain the single source of validation truth;
these models exist purely so flask-openapi3 can describe the request/response shapes.
"""
from pydantic import BaseModel
from typing import Optional


# ─── Request Bodies ────────────────────────────────────────────────

class RegisterBody(BaseModel):
    """Body for POST /auth/register"""
    username: str
    email: str
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
    """Body for POST /auth/verify-otp"""
    email: str
    otp: str

    model_config = {
        "json_schema_extra": {
            "example": {"email": "john@example.com", "otp": "482910"}
        }
    }


class LoginBody(BaseModel):
    """Body for POST /auth/login — accepts email OR username as identifier"""
    identifier: str
    password: str

    model_config = {
        "json_schema_extra": {
            "example": {"identifier": "john@example.com", "password": "Secure@123"}
        }
    }


class PasswordResetRequestBody(BaseModel):
    """Body for POST /auth/password-reset/request"""
    email: str

    model_config = {
        "json_schema_extra": {"example": {"email": "john@example.com"}}
    }


class PasswordResetVerifyBody(BaseModel):
    """Body for POST /auth/password-reset/verify"""
    email: str
    otp: str

    model_config = {
        "json_schema_extra": {
            "example": {"email": "john@example.com", "otp": "837201"}
        }
    }


class PasswordResetConfirmBody(BaseModel):
    """Body for POST /auth/password-reset/confirm"""
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
    """Body for POST /auth/refresh"""
    refresh_token: str

    model_config = {
        "json_schema_extra": {
            "example": {"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
        }
    }


class ResendOTPBody(BaseModel):
    """Body for POST /auth/resend-otp"""
    email: str

    model_config = {
        "json_schema_extra": {"example": {"email": "john@example.com"}}
    }


# ─── Response Models ──────────────────────────────────────────────

class UserOut(BaseModel):
    id: str
    username: str
    email: str
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
