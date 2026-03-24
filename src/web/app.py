from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from src.web.routes.pages import router as pages_router
from src.web.routes.api import router as api_router

BASE_DIR = Path(__file__).parent


def create_app() -> FastAPI:
    app = FastAPI(title="Hearthstone Deck Maker")

    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

    app.include_router(pages_router)
    app.include_router(api_router, prefix="/api")

    return app


templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app = create_app()
