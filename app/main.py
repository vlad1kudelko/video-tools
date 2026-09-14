from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .app_materials.routes import router as materials_router
from .app_reframe.routes import router as reframe_router
from .config import MATERIALS_STATIC, REFRAME_STATIC, STATIC, TMP

app = FastAPI()
app.include_router(reframe_router)
app.include_router(materials_router)


@app.on_event("startup")
def _startup() -> None:
    TMP.mkdir(parents=True, exist_ok=True)


# Specific static mounts must be registered before the catch-all "/" mount,
# otherwise it swallows every request first.
app.mount("/reframe-static", StaticFiles(directory=REFRAME_STATIC), name="reframe-static")
app.mount("/materials-static", StaticFiles(directory=MATERIALS_STATIC), name="materials-static")
app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
