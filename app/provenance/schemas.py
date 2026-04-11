from marshmallow import Schema, fields

class ProvenanceReportSchema(Schema):
    filename = fields.String()
    media_type = fields.String()
    provenance_score = fields.Float()
    metadata_anomalies = fields.List(fields.String())
    metadata_extracted = fields.Dict()
    ai_generation_indicators = fields.List(fields.String())
    risk_level = fields.String()