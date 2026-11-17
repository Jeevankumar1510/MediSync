from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api.v1.router import api_router
from app.api.v1.endpoints import (
    health,
    auth,
    patients,
    integrations,
    mock_ehr,
    normalization,
    sync,
    monitoring,
    webhooks,
    ai,
    rag,
)

# Configure standard logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("medisync.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info(f"Starting {settings.PROJECT_NAME} in [{settings.ENVIRONMENT}] mode...")
    yield
    # Shutdown actions
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Intelligent Healthcare Data Integration & RAG Platform - Standardized FHIR Engine, Background Sync & AI Assistant",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Register direct monitoring health endpoint (required by specification: GET /monitoring/health)
app.include_router(health.router, prefix="/monitoring", tags=["Monitoring"])

# Root alias for authentication (required by specification: POST /auth/register, POST /auth/login)
app.include_router(auth.router, prefix="/auth", tags=["Authentication & RBAC"])

# Root alias for patients (required by specification: GET /patients, POST /patients)
app.include_router(patients.router, prefix="/patients", tags=["Patients & FHIR Records"])

# Root alias for integrations (required by specification: GET /integrations, POST /integrations, POST /integrations/{id}/sync)
app.include_router(integrations.router, prefix="/integrations", tags=["API Integrations"])

# Root alias for normalization engine
app.include_router(normalization.router, prefix="/normalization", tags=["Data Normalization & FHIR Validator"])

# Root alias for synchronization engine
app.include_router(sync.router, prefix="/sync", tags=["Synchronization Engine"])

# Root alias for webhooks (required by specification: POST /webhooks/events, GET /webhooks/events, POST /webhooks/events/{id}/retry)
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhook Management"])

# Root alias for AI engine (required by specification: POST /ai/map-fields, POST /ai/analyze, POST /ai/explain-error)
app.include_router(ai.router, prefix="/ai", tags=["AI Field Mapping & Data Quality"])

# Root alias for RAG healthcare assistant (required by specification: POST /rag/upload, POST /rag/query, GET /rag/documents)
app.include_router(rag.router, prefix="/rag", tags=["RAG Healthcare Assistant"])

# System monitoring endpoints (GET /monitoring/health, GET /monitoring/api-logs, GET /monitoring/sync-statistics)
app.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring & Analytics"])

# Mount mock EHR services at root for external simulation
app.include_router(mock_ehr.router, tags=["Mock Healthcare Services"])


@app.get(
    "/",
    tags=["Root"],
    summary="MediSync AI API Root",
    status_code=status.HTTP_200_OK
)
async def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "online",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": f"{settings.API_V1_STR}/openapi.json"
        },
        "health_check": "/monitoring/health"
    }

