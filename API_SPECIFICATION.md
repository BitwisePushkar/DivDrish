# DivDrish — DeepTrace ML Engine API Specification v2.0.0

Base URL: http://localhost:8000
Swagger UI: http://localhost:8000/openapi/swagger

================================================================================
GLOBAL RESPONSE FORMAT
================================================================================

All responses follow this standardized wrapper:

SUCCESS (2xx):
{
  "status": "success",
  "message": "Human readable summary",
  "data": { ... },
  "request_id": "uuid"
}

ERROR (4xx / 5xx):
{
  "status": "error",
  "error": "Short error description",
  "detail": "Longer explanation or validation error object",
  "status_code": 400,
  "request_id": "uuid"
}

================================================================================
AUTHENTICATION
================================================================================

Protected routes require one of:
  - Header: Authorization: Bearer <access_token>
  - Header: X-API-Key: <api_key>

================================================================================
1. HEALTH
================================================================================

GET /health
  Auth: None
  Response 200:
  {
    "status": "ok",
    "version": "2.0.0",
    "gpu_available": false,
    "models_loaded": { "image": false, "video": false, "audio": false }
  }

================================================================================
2. AUTH — REGISTRATION (2-Step OTP Flow)
================================================================================

POST /auth/register
  Auth: None
  Rate Limit: 5/minute
  Body (JSON):
  {
    "username": "johndoe",
    "email": "john@example.com",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!"
  }
  Response 201:
  {
    "status": "success",
    "data": {
      "message": "Verification code sent to email",
      "email": "john@example.com"
    }
  }

--------------------------------------------------------------------------------

POST /auth/verify-otp
  Auth: None
  Rate Limit: 10/minute
  Body (JSON):
  {
    "email": "john@example.com",
    "otp": "654321"
  }
  Response 201:
  {
    "status": "success",
    "message": "Account verified successfully",
    "data": {
      "access_token": "eyJhbG...",
      "refresh_token": "eyJhbG...",
      "token_type": "bearer",
      "expires_in": 86400,
      "user": {
        "id": "uuid",
        "username": "johndoe",
        "display_name": null,
        "email": "john@example.com",
        "profile_image_url": null,
        "is_active": true,
        "created_at": "2026-04-10T..."
      }
    }
  }

--------------------------------------------------------------------------------

POST /auth/resend-otp
  Auth: None
  Rate Limit: 3/minute
  Body (JSON):
  { "email": "john@example.com" }
  Response 200:
  { "data": { "message": "New verification code sent to email", "email": "..." } }

================================================================================
3. AUTH — LOGIN & TOKENS
================================================================================

POST /auth/login
  Auth: None
  Rate Limit: 10/minute
  Body (JSON):
  {
    "identifier": "johndoe OR john@example.com",
    "password": "SecurePass123!"
  }
  Response 200: (Same structure as verify-otp — returns tokens + user)

--------------------------------------------------------------------------------

POST /auth/refresh
  Auth: None
  Body (JSON):
  { "refresh_token": "eyJhbG..." }
  Response 200:
  {
    "data": {
      "access_token": "eyJhbG... (new)",
      "token_type": "bearer",
      "expires_in": 86400
    }
  }

================================================================================
4. AUTH — PASSWORD RESET (3-Step Flow)
================================================================================

POST /auth/password-reset/request
  Body: { "email": "john@example.com" }
  Response 200: { "data": { "message": "Verification code sent to email" } }

POST /auth/password-reset/verify
  Body: { "email": "john@example.com", "otp": "837201" }
  Response 200: { "data": { "reset_token": "a3f1c9d8...", "message": "Code verified." } }

POST /auth/password-reset/confirm
  Body: { "email": "john@example.com", "reset_token": "a3f1c9d8...", "new_password": "NewPassword456!" }
  Response 200: { "data": { "message": "Password updated successfully" } }

================================================================================
5. AUTH — USER PROFILE
================================================================================

GET /auth/me
  Auth: JWT Required
  Response 200:
  {
    "data": {
      "id": "uuid",
      "username": "johndoe",
      "display_name": "John Doe",
      "email": "john@example.com",
      "profile_image_url": "https://bucket.s3.amazonaws.com/avatars/uuid/profile.jpg",
      "is_active": true,
      "created_at": "2026-04-10T..."
    }
  }

--------------------------------------------------------------------------------

PUT /auth/profile
  Auth: JWT Required
  Description: Update display name and/or username. Both fields are optional.
  Body (JSON):
  {
    "display_name": "John Doe",
    "username": "johndoe_new"
  }
  Response 200:
  {
    "status": "success",
    "message": "Profile updated successfully",
    "data": {
      "id": "uuid",
      "username": "johndoe_new",
      "display_name": "John Doe",
      "email": "john@example.com",
      "profile_image_url": null,
      "is_active": true,
      "created_at": "2026-04-10T..."
    }
  }
  Error 400: { "error": "Username already taken" }
  Error 400: { "error": "Username must be between 5 and 50 characters" }
  Error 400: { "error": "Display name must be 100 characters or less" }

--------------------------------------------------------------------------------

POST /auth/profile/avatar
  Auth: JWT Required
  Description: Upload or replace profile image. Stored in AWS S3.
  Body (multipart/form-data):
    file: Binary image (image/jpeg, image/png, image/webp). Max 5MB.
  Response 200:
  {
    "status": "success",
    "message": "Avatar updated successfully",
    "data": {
      "id": "uuid",
      "username": "johndoe",
      "display_name": "John Doe",
      "email": "john@example.com",
      "profile_image_url": "https://bucket.s3.us-east-1.amazonaws.com/avatars/uuid/profile.jpg",
      "is_active": true,
      "created_at": "2026-04-10T..."
    }
  }
  Error 400: { "error": "No file provided. Use 'file' field." }
  Error 422: { "error": "Unsupported image type: application/pdf. Allowed: image/jpeg, image/png, image/webp" }
  Error 422: { "error": "File too large: >5MB limit" }

================================================================================
6. DETECTION
================================================================================

POST /detect
  Auth: JWT Required
  Description: Auto-detect media type (image/video/audio) and analyze.
  Body (multipart/form-data):
    file: Binary file
  Response 200:
  {
    "data": {
      "media_type": "image",
      "is_fake": true,
      "confidence": 0.985,
      "recommendation": "high_risk",
      "processing_time_ms": 1250,
      "file_size_mb": 2.4,
      "resolution": "1920x1080",
      "model_fingerprint": "...",
      "artifact_signatures": [...],
      "metadata_anomalies": [...],
      "provenance_score": 0.12
    }
  }

--------------------------------------------------------------------------------

POST /detect/image
POST /detect/video
POST /detect/audio
  Same as /detect but forces a specific media type processor.

--------------------------------------------------------------------------------

POST /detect/batch
  Auth: JWT Required
  Body (multipart/form-data):
    files: Up to 10 binary files (key = "files" for each)
  Response 200:
  {
    "data": {
      "total_files": 3,
      "processed": 2,
      "fake_count": 1,
      "average_confidence": 0.75,
      "results": [
        { "filename": "photo.jpg", "success": true, "result": { ...detection... }, "error": null },
        { "filename": "bad.pdf", "success": false, "result": null, "error": "Unsupported media type" }
      ]
    }
  }

--------------------------------------------------------------------------------

POST /detect/async/<media_type>
  Auth: JWT Required
  media_type: "image" | "video" | "audio"
  Body (multipart/form-data): file
  Response 202:
  { "data": { "task_id": "celery-uuid", "status": "PROCESSING", "message": "Async image detection started" } }

POST /detect/async/batch
  Auth: JWT Required
  Body (multipart/form-data): files (multiple)
  Response 202:
  { "data": { "task_id": "celery-uuid", "status": "PROCESSING", "total_files": 3 } }

GET /task/<task_id>
  Auth: JWT Required
  Response 200:
  {
    "data": {
      "task_id": "...",
      "status": "PENDING | SUCCESS | FAILURE",
      "result": { ...detection payload if SUCCESS... },
      "error": "error message if FAILURE"
    }
  }

================================================================================
7. COMMUNITY FEED
================================================================================

GET /community/posts
  Auth: None (public)
  Query Params: ?page=1&page_size=20
  Response 200:
  {
    "data": {
      "items": [
        {
          "id": "post-uuid",
          "title": "Detected a deepfake video",
          "description": "Notice the artifacts around the jawline.",
          "created_at": "2026-04-10T...",
          "author": {
            "username": "johndoe",
            "display_name": "John Doe",
            "profile_image_url": "https://...s3.../avatars/uuid/profile.jpg"
          },
          "analysis": {
            "media_type": "video",
            "is_fake": true,
            "confidence": 0.99,
            "recommendation": "high_risk",
            "file_hash": "sha256...",
            "media_url": "https://...s3.../history/uuid/record_file.mp4"
          }
        }
      ],
      "total": 42,
      "page": 1,
      "page_size": 20
    }
  }

--------------------------------------------------------------------------------

POST /community/posts
  Auth: JWT Required
  Description: Share an analysis result. You must own the analysis_id.
  Body (JSON):
  {
    "analysis_id": "uuid-from-a-detection-response",
    "title": "Optional title",
    "description": "Optional description"
  }
  Response 201: Returns the created post object (same shape as items above).
  Error 400: "Analysis not found or does not belong to the user"
  Error 400: "Analysis already posted to the community"

--------------------------------------------------------------------------------

GET /community/posts/<post_id>
  Auth: None
  Response 200: Single post object.
  Error 404: "Post not found"

--------------------------------------------------------------------------------

DELETE /community/posts/<post_id>
  Auth: JWT Required (must be the author)
  Response 200: { "data": { "message": "Post deleted successfully" } }
  Error 404: "Post not found or unauthorized"

================================================================================
8. HISTORY & STATISTICS
================================================================================

All endpoints are scoped to the authenticated user. Users can only see their own data.

GET /history
  Auth: JWT Required
  Query Params: ?page=1&page_size=20&media_type=image&is_fake=true
  Response 200:
  {
    "data": {
      "total": 15,
      "page": 1,
      "page_size": 20,
      "results": [
        {
          "id": "analysis-uuid",
          "timestamp": "2026-04-10T...",
          "media_type": "image",
          "filename": "photo.jpg",
          "file_hash": "sha256...",
          "media_url": "https://...s3.../history/...",
          "is_fake": true,
          "confidence": 0.97,
          "recommendation": "high_risk",
          "processing_time_ms": 450,
          "file_size_mb": 3.2,
          "resolution": "1920x1080"
        }
      ]
    }
  }

--------------------------------------------------------------------------------

GET /history/stats
  Auth: JWT Required
  Response 200:
  {
    "data": {
      "total_scans": 150,
      "fake_count": 12,
      "real_count": 138,
      "fake_percentage": 8.0,
      "average_confidence": 0.82,
      "by_media_type": { "image": 100, "video": 40, "audio": 10 },
      "by_recommendation": { "high_risk": 12, "safe": 138 }
    }
  }

--------------------------------------------------------------------------------

GET /history/<record_id>
  Auth: JWT Required
  Response 200: Full analysis record object.
  Error 404: "Record not found"

DELETE /history/<record_id>
  Auth: JWT Required
  Response 200: { "data": { "message": "Record deleted successfully", "id": "..." } }
  Error 404: "Record not found"

================================================================================
9. PROVENANCE ANALYSIS
================================================================================

POST /provenance/analyze
  Auth: JWT Required
  Description: Extracts metadata/EXIF data for origin tracing. No ML inference.
  Body (multipart/form-data):
    file: Binary file (image, video, or audio)
  Response 200: EXIF data, modification history, origin tracking results.

================================================================================
SUPPORTED FILE TYPES
================================================================================

Image: image/jpeg, image/png, image/webp, image/bmp
Video: video/mp4, video/mpeg, video/webm, video/quicktime
Audio: audio/mpeg, audio/wav, audio/ogg, audio/flac, audio/mp4

Upload Limits:
  Image: 20 MB
  Video: 200 MB
  Audio: 50 MB
  Avatar: 5 MB

================================================================================
ERROR CODES REFERENCE
================================================================================

400 - Bad Request / Validation error
401 - Authentication required / Invalid token / Token expired
403 - Forbidden / Invalid API key
404 - Resource not found
413 - File exceeds maximum upload size
422 - Unsupported media/file type or validation failure
429 - Rate limit exceeded
500 - Internal server error
