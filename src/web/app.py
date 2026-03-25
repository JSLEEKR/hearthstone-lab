from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from src.web.routes.pages import router as pages_router
from src.web.routes.api import router as api_router
from src.web.i18n import get_all_translations, DEFAULT_LANG, SUPPORTED_LANGS

BASE_DIR = Path(__file__).parent


def create_app() -> FastAPI:
    app = FastAPI(title="Hearthstone Lab")

    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

    @app.middleware("http")
    async def language_middleware(request: Request, call_next):
        lang = request.query_params.get("lang", "")
        if lang not in SUPPORTED_LANGS:
            lang = request.cookies.get("lang", DEFAULT_LANG)
        if lang not in SUPPORTED_LANGS:
            lang = DEFAULT_LANG
        request.state.lang = lang
        response = await call_next(request)
        response.set_cookie("lang", lang, max_age=365 * 24 * 3600)
        return response

    app.include_router(pages_router)
    app.include_router(api_router, prefix="/api")

    return app


app = create_app()
