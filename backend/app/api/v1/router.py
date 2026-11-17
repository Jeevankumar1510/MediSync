from fastapi import APIRouter
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

api_router = APIRouter()

# Health & Diagnostics
api_router.include_router(health.router, tags=["Health & Monitoring"])

# Module 1: Authentication & RBAC
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & RBAC"])

# Module 2: Patients & Clinical Records
api_router.include_router(patients.router, prefix="/patients", tags=["Patients & FHIR Records"])

# Module 3: Healthcare API Integrations
api_router.include_router(integrations.router, prefix="/integrations", tags=["API Integrations"])

# Module 4: Data Normalization Engine
api_router.include_router(normalization.router, prefix="/normalization", tags=["Data Normalization & FHIR Validator"])

# Module 5: Synchronization Engine
api_router.include_router(sync.router, prefix="/sync", tags=["Synchronization Engine"])

# Module 6: Webhook Management
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhook Management"])

# Module 7 & 9: AI Field Mapping & Clinical Data Quality
api_router.include_router(ai.router, prefix="/ai", tags=["AI Field Mapping & Data Quality"])

# Module 8: RAG Healthcare Assistant & Knowledge Base
api_router.include_router(rag.router, prefix="/rag", tags=["RAG Healthcare Assistant"])

# System Monitoring & Analytics
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring & Analytics"])

# Built-in Mock Healthcare Server (FHIR R4 & Proprietary Vendor)
api_router.include_router(mock_ehr.router, tags=["Mock Healthcare Services"])
