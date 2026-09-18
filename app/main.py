from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .app_combinator.routes import router as combinator_router
from .app_concat.routes import router as concat_router
from .app_download.routes import router as download_router
from .app_materials.routes import router as materials_router
from .app_record.routes import router as record_router
from .app_reframe.routes import router as reframe_router
from .config import (
    CANVAS_STATIC,
    COMBINATOR_STATIC,
    CONCAT_STATIC,
    DOWNLOAD_STATIC,
    MATERIALS_STATIC,
    RECORD_STATIC,
    REFRAME_STATIC,
    STATIC,
    TMP,
)
from .pipeline import manifests  # noqa: F401  — registers all module manifests on import
from .pipeline.routes import router as pipeline_router

app = FastAPI()
app.include_router(reframe_router)
app.include_router(materials_router)
app.include_router(download_router)
app.include_router(record_router)
app.include_router(concat_router)
app.include_router(combinator_router)
app.include_router(pipeline_router)


@app.on_event("startup")
def _startup() -> None:
    TMP.mkdir(parents=True, exist_ok=True)


# Specific static mounts must be registered before the catch-all "/" mount,
# otherwise it swallows every request first.
app.mount("/reframe-static", StaticFiles(directory=REFRAME_STATIC), name="reframe-static")
app.mount("/materials-static", StaticFiles(directory=MATERIALS_STATIC), name="materials-static")
app.mount("/download-static", StaticFiles(directory=DOWNLOAD_STATIC), name="download-static")
app.mount("/record-static", StaticFiles(directory=RECORD_STATIC), name="record-static")
app.mount("/concat-static", StaticFiles(directory=CONCAT_STATIC), name="concat-static")
app.mount("/combinator-static", StaticFiles(directory=COMBINATOR_STATIC), name="combinator-static")
app.mount("/canvas", StaticFiles(directory=CANVAS_STATIC, html=True, check_dir=False), name="canvas")
app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
