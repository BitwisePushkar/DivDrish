"""
Marshmallow schemas for Community feature.
"""
from marshmallow import Schema, fields, validate

class PostCreateSchema(Schema):
    analysis_id = fields.String(required=True)
    title = fields.String(required=False, validate=validate.Length(max=255))
    description = fields.String(required=False)
    
class PaginationSchema(Schema):
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    page_size = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))
