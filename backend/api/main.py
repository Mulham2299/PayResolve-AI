import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.api.routes import router as api_router

load_dotenv()

app = FastAPI(
    title="PayResolve AI — Multi-Agent Dispute & Settlement Swarm API",
    description=(
        "Autonomous 6-Agent Customer Dispute Triage, Fraud Risk Scoring, and "
        "Instant PayPal Sandbox Settlement Engine built for the PayPal AI Hackathon 2026."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    """Health check endpoint verifying environment configuration."""
    return {
        "status": "ok",
        "service": "PayResolve AI Swarm Backend",
        "paypal_mode": os.getenv("PAYPAL_MODE", "sandbox"),
        "paypal_configured": bool(
            os.getenv("PAYPAL_CLIENT_ID") and os.getenv("PAYPAL_CLIENT_SECRET")
        ),
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
    }

