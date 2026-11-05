from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from backend.api.v1.chat import router as chat_router


from backend.config import settings
from backend.database.connection import get_db
from backend.api.v1.catalogue import router as catalogue_router
from backend.api.v1.sources import router as sources_router
from backend.api.v1.services import router as services_router

from fastapi.middleware.cors import CORSMiddleware
from backend.api.v1 import verification
from backend.api.v1.admin_auth import router as admin_auth_router
from backend.api.v1.auth import router as citizen_auth_router
from backend.api.v1.users import router as users_router
from backend.api.v1.admin import router as admin_router
from backend.api.v1.voice import router as voice_router





app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered Indian Government Services Assistance Platform",
    debug=settings.DEBUG,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(catalogue_router, prefix=settings.API_V1_PREFIX)
app.include_router(sources_router, prefix=settings.API_V1_PREFIX)
app.include_router(services_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    return {
        "message": "Welcome to SchemeSathi 2.0",
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/health/database")
def database_health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "connected",
            "database": "MySQL",
            "message": "Database connection successful",
        }
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        )
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(verification.router, prefix="/api/v1")

app.include_router(
    admin_auth_router,
    prefix="/api/v1",
)

app.include_router(voice_router, prefix=settings.API_V1_PREFIX)

app.include_router(chat_router, prefix=settings.API_V1_PREFIX)

app.include_router(citizen_auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(users_router, prefix=settings.API_V1_PREFIX)
app.include_router(admin_router, prefix=settings.API_V1_PREFIX)
