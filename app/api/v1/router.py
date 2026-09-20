from fastapi import APIRouter

from app.api.v1.endpoints import auth, job, candidate, shortlist, application, notification_preference

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(job.router)
api_router.include_router(candidate.router)
api_router.include_router(shortlist.router)
api_router.include_router(application.router)
api_router.include_router(notification_preference.router)