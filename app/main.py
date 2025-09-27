from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import logging

from app.core.config import settings
from app.api.v1 import auth, households, planning, receipts, settlements, splitwise

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MealSplit API",
    description="OCR-based grocery receipt splitting app",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(households.router, prefix=f"{settings.API_V1_STR}/households", tags=["households"])
app.include_router(planning.router, prefix=f"{settings.API_V1_STR}/planning", tags=["planning"])
app.include_router(receipts.router, prefix=f"{settings.API_V1_STR}/receipts", tags=["receipts"])
app.include_router(settlements.router, prefix=f"{settings.API_V1_STR}/settlements", tags=["settlements"])
app.include_router(splitwise.router, prefix=f"{settings.API_V1_STR}/splitwise", tags=["splitwise"])

@app.get("/")
async def root():
    return {"message": "MealSplit API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}