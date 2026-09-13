from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import MATERIALS_STATIC, STATIC, TMP, VIDEO_STATIC
from .materials.routes import router as materials_router
from .video.routes import router as video_router

app = FastAPI()
app.include_router(video_router)
app.include_router(materials_router)


@app.on_event("startup")
def _startup() -> None:
    TMP.mkdir(parents=True, exist_ok=True)


# Specific static mounts must be registered before the catch-all "/" mount,
# otherwise it swallows every request first.
app.mount("/video-static", StaticFiles(directory=VIDEO_STATIC), name="video-static")
app.mount("/materials-static", StaticFiles(directory=MATERIALS_STATIC), name="materials-static")
app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
