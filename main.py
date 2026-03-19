from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.database import engine, Base
from app.core.config import settings
import app.models  # noqa: F401 - register all models

app = FastAPI(title=settings.APP_NAME, version="1.0.0")

@app.on_event("startup")
def on_startup() -> None:
    # For this small project we auto-create tables on startup.
    # In production you would use Alembic migrations.
    if settings.DB_AUTO_CREATE:
        Base.metadata.create_all(bind=engine)


# Static files (optional)
static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.middleware("http")
async def security_headers_middleware(request, call_next):
    response = await call_next(request)
    # Basic security headers for HTML apps.
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=()")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    # Avoid caching authenticated pages.
    if request.url.path.startswith("/auth") or request.url.path.startswith("/settings"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response

# Register routers
from app.routes.auth import router as auth_router
from app.routes.dashboard import router as dashboard_router
from app.routes.transactions import router as transaction_router
from app.routes.categories import router as category_router
from app.routes.cards import router as card_router
from app.routes.goals import router as goal_router
from app.routes.reports import router as report_router
from app.routes.settings import router as settings_router
from app.routes.accounts import router as accounts_router

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(transaction_router)
app.include_router(category_router)
app.include_router(card_router)
app.include_router(goal_router)
app.include_router(report_router)
app.include_router(settings_router)
app.include_router(accounts_router)
