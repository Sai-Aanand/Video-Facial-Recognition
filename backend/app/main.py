from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.video_routes import router as video_router
from .core.config import settings

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(video_router)


@app.get("/health")
async def healthcheck():
    return {"status": "ok"}
