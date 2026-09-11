from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import STATIC, TMP
from .routes import router

app = FastAPI()
app.include_router(router)


@app.on_event("startup")
def _startup() -> None:
    TMP.mkdir(parents=True, exist_ok=True)


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
