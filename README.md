# DeepTrace ML Engine (Flask Rebuild)

Production-grade Flask backend for deepfake detection, featuring Celery for asynchronous processing, Redis, PostgreSQL, and dual authentication.

## 🚀 Features

- **Flask Blueprints** for modular architecture
- **Celery + Redis** for asynchronous heavy ML task processing
- **Dual Authentication**: JWT Bearer Tokens AND API Keys
- **Advanced AI Detection**: Enhanced metadata analysis to detect ComfyUI, DALL-E, Midjourney, etc.
- **Docker Ready**: Multi-container setup with Flask, Celery, Redis, and Postgres

## 📁 Architecture

```
flask_backend/
├── app/
│   ├── auth/          # JWT/API Key auth routes
│   ├── detection/     # Media detection endpoints
│   ├── history/       # CRUD for past scans
│   ├── provenance/    # Metadata analysis
│   ├── health/        # System status
│   ├── models/        # ML Models (EfficientNet, LCNN)
│   ├── services/      # Analysis logic
│   └── database/      # SQLAlchemy ORM
```

## 🛠️ Local Development (Without Docker)

1. **Install Dependencies (Python 3.13 recommended)**:
   ```bash
   # Install torch first
   pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cpu
   
   # Install requirements
   pip install -r requirements.txt
   pip install facenet-pytorch>=2.6.0 --no-deps
   ```

2. **Setup Redis and PostgreSQL**:
   You must have Redis running locally for Celery, and PostgreSQL for the DB.

3. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your DB and Redis URIs
   ```

4. **Run DB Migrations (Auto-created on start)**:
   Database tables are created automatically on app startup.

5. **Run Flask App**:
   ```bash
   flask run --debug
   # OR using Gunicorn
   gunicorn wsgi:app
   ```

6. **Run Celery Worker (In a separate terminal)**:
   ```bash
   celery -A app.extensions.celery worker --loglevel=info
   ```

## 🐳 Docker Deployment (Recommended)

1. **Copy weights into `../weights/`** (assuming they exist in the parent folder).
2. **Start the cluster**:
   ```bash
   docker-compose up -d --build
   ```

### Services Started:
- `deeptrace-flask-api`: http://localhost:8000
- `deeptrace-celery-worker`: Background ML tasks
- `deeptrace-redis`: localhost:6379
- `deeptrace-flask-db`: localhost:5433

## 🔐 Authentication

All routes except `/health` are protected. You can authenticate via:

1. **API Key Header**: `X-API-Key: dt_your_api_key_here`
2. **JWT Bearer Token**: `Authorization: Bearer <token>`
   - Get a token by hitting `POST /auth/register` then `POST /auth/login`.

*(In development, if no `API_KEYS` are defined in `.env` and `SECRET_KEY` is left as default, auth is disabled/bypassed.)*
