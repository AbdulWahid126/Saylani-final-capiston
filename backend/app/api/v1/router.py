from fastapi import APIRouter

from app.api.v1.endpoints import (
    accounts,
    analytics,
    auth,
    behavior,
    health,
    journal,
    learning,
    playbook,
    reviewer,
    risk,
    vision,
)

api_v1_router = APIRouter()

# Register core v1 endpoints
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(accounts.router)
api_v1_router.include_router(journal.router)
api_v1_router.include_router(analytics.router)
api_v1_router.include_router(risk.router)
api_v1_router.include_router(behavior.router)
api_v1_router.include_router(playbook.router)
api_v1_router.include_router(reviewer.router)
api_v1_router.include_router(vision.router)
api_v1_router.include_router(learning.router)
