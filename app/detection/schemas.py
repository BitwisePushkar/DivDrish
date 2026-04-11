from marshmallow import Schema, fields

class ArtifactSignatureSchema(Schema):
    name = fields.String()
    detected = fields.Boolean()
    severity = fields.Float()
    description = fields.String()

class FrameResultSchema(Schema):
    frame_index = fields.Integer()
    timestamp_sec = fields.Float()
    confidence = fields.Float()
    face_detected = fields.Boolean()

class DetectionResultSchema(Schema):
    media_type = fields.String()
    is_fake = fields.Boolean()
    confidence = fields.Float()
    model_fingerprint = fields.String(allow_none=True)
    artifact_signatures = fields.List(fields.Nested(ArtifactSignatureSchema))
    frame_analysis = fields.List(fields.Nested(FrameResultSchema), allow_none=True)
    processing_time_ms = fields.Float()
    file_size_mb = fields.Float()
    resolution = fields.String(allow_none=True)
    metadata_anomalies = fields.List(fields.String())
    ai_generation_indicators = fields.List(fields.String())
    provenance_score = fields.Float(allow_none=True)
    recommendation = fields.String()

class BatchItemResultSchema(Schema):
    filename = fields.String()
    success = fields.Boolean()
    result = fields.Nested(DetectionResultSchema, allow_none=True)
    error = fields.String(allow_none=True)

class BatchResultSchema(Schema):
    total_files = fields.Integer()
    processed = fields.Integer()
    fake_count = fields.Integer()
    average_confidence = fields.Float()
    results = fields.List(fields.Nested(BatchItemResultSchema))

class TaskStatusSchema(Schema):
    task_id = fields.String()
    status = fields.String()
    result = fields.Nested(DetectionResultSchema, allow_none=True)
    error = fields.String(allow_none=True)