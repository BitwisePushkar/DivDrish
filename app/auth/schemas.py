"""
Marshmallow schemas for authentication.
"""
from marshmallow import Schema, fields, validate, validates, ValidationError


class RegisterSchema(Schema):
    """Schema for user registration."""
    email = fields.Email(required=True, metadata={"description": "User email"})
    password = fields.String(
        required=True,
        validate=validate.Length(min=8, max=128),
        metadata={"description": "Password (min 8 chars)"},
    )


class LoginSchema(Schema):
    """Schema for user login."""
    email = fields.Email(required=True)
    password = fields.String(required=True)


class TokenResponseSchema(Schema):
    """Schema for JWT token response."""
    access_token = fields.String()
    refresh_token = fields.String()
    token_type = fields.String(dump_default="bearer")
    expires_in = fields.Integer()


class RefreshSchema(Schema):
    """Schema for token refresh."""
    refresh_token = fields.String(required=True)


class UserSchema(Schema):
    """Schema for user info response."""
    id = fields.String()
    email = fields.Email()
    api_key = fields.String(allow_none=True)
    is_active = fields.Boolean()
    created_at = fields.DateTime()
