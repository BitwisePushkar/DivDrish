from marshmallow import Schema, fields, validate, validates, ValidationError, validates_schema

class RegisterSchema(Schema):
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
    email = fields.Email(required=True)
    otp = fields.String(required=True, validate=validate.Length(equal=6))

class LoginSchema(Schema):
    identifier = fields.String(required=True, metadata={"description": "Email or Username"})
    password = fields.String(required=True)

class PasswordResetRequestSchema(Schema):
    email = fields.Email(required=True)

class PasswordResetConfirmSchema(Schema):
    email = fields.Email(required=True)
    reset_token = fields.String(required=True)
    new_password = fields.String(required=True, validate=validate.Length(min=8))

class TokenResponseSchema(Schema):
    access_token = fields.String()
    refresh_token = fields.String()
    token_type = fields.String(dump_default="bearer")
    expires_in = fields.Integer()

class RefreshSchema(Schema):
    refresh_token = fields.String(required=True)

class ResendOTPSchema(Schema):
    email = fields.Email(required=True)

class UserSchema(Schema):
    id = fields.String()
    username = fields.String()
    email = fields.Email()
    api_key = fields.String(allow_none=True)
    is_active = fields.Boolean()
    created_at = fields.DateTime()