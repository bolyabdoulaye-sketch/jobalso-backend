from fastapi import APIRouter

from app.api.v1.endpoints import auth, candidature, cv, offre, public

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(cv.router)
api_router.include_router(offre.router)
api_router.include_router(candidature.router)
api_router.include_router(public.router)
