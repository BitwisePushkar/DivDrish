"""
Marshmallow schemas for history endpoints.
"""
from marshmallow import Schema, fields


class AnalysisRecordSchema(Schema):
    id = fields.String()
    timestamp = fields.String()
    media_type = fields.String()
    filename = fields.String()
    file_hash = fields.String()
    is_fake = fields.Boolean()
    confidence = fields.Float()
    model_fingerprint = fields.String(allow_none=True)
    provenance_score = fields.Float(allow_none=True)
    processing_time_ms = fields.Float()
    file_size_mb = fields.Float()
    resolution = fields.String(allow_none=True)
    recommendation = fields.String()


class PaginatedHistorySchema(Schema):
    total = fields.Integer()
    page = fields.Integer()
    page_size = fields.Integer()
    results = fields.List(fields.Nested(AnalysisRecordSchema))


class AnalysisStatsSchema(Schema):
    total_scans = fields.Integer()
    fake_count = fields.Integer()
    real_count = fields.Integer()
    fake_percentage = fields.Float()
    average_confidence = fields.Float()
    by_media_type = fields.Dict()
    by_recommendation = fields.Dict()
