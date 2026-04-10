"""
Marshmallow schemas for authentication.
"""
from marshmallow import Schema, fields, validate, validates, ValidationError, validates_schema


class RegisterSchema(Schema):
    """Schema for initial user registration."""
    username = fields.String(
        required=True, 
        validate=[
            validate.Length(min=5, max=50),
            validate.Regexp(
                r"^[a-zA-Z0-9_@#]+$", 
                error="Username can only contain letters, numbers, underscores, @ and #"
            )
        ]
    )
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=8))
    password_confirm = fields.String(required=True)

    @validates_schema
    def validate_password_confirm(self, data, **kwargs):
        if data.get("password") != data.get("password_confirm"):
            raise ValidationError("Passwords do not match", "password_confirm")


class VerifyOTPSchema(Schema):
    """Schema for OTP verification."""
    email = fields.Email(required=True)
    otp = fields.String(required=True, validate=validate.Length(equal=6))


class LoginSchema(Schema):
    """Schema for user login (supports email or username)."""
    identifier = fields.String(required=True, metadata={"description": "Email or Username"})
    password = fields.String(required=True)


class PasswordResetRequestSchema(Schema):
    """Schema for password reset request."""
    email = fields.Email(required=True)


class PasswordResetConfirmSchema(Schema):
    """Schema for password reset confirmation."""
    email = fields.Email(required=True)
    reset_token = fields.String(required=True)
    new_password = fields.String(required=True, validate=validate.Length(min=8))
class TokenResponseSchema(Schema):
    """Schema for JWT token response."""
    access_token = fields.String()
    refresh_token = fields.String()
    token_type = fields.String(dump_default="bearer")
    expires_in = fields.Integer()


class RefreshSchema(Schema):
    """Schema for token refresh."""
    refresh_token = fields.String(required=True)


class ResendOTPSchema(Schema):
    """Schema for requesting an OTP resend."""
    email = fields.Email(required=True)


class UserSchema(Schema):
    """Schema for user info response."""
    id = fields.String()
    username = fields.String()
    email = fields.Email()
    api_key = fields.String(allow_none=True)
    is_active = fields.Boolean()
    created_at = fields.DateTime()
