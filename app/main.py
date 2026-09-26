import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import auth, offres, cv, banque_profils, candidature
from app.core.config import settings

logging.basicConfig(level=logging.DEBUG if settings.app_debug else logging.INFO)

app= FastAPI(
    title="Mon API",
    version="1.0"
)
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
app.include_router(auth.router)
app.include_router(offres.router)
app.include_router(cv.router)
app.include_router(banque_profils.router)
app.include_router(candidature.router)
@app.get("/")
async def root():
    return{
        "message": "ca fonctionne"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=12333, reload=True)    
