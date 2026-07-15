import os, sys, logging
from pathlib import Path
from dotenv import load_dotenv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session as DBSession
from backend.database import init_db, get_db, SessionLocal
from backend.routers import knowmap, upload, tutor, learn, settings, auth, admin, review, health, referral
from backend.services.runtime_config import load_runtime_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI(title="MathMind - ShuZhiXueTang", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def ensure_initial_accounts(db, runtime_config):
    """Create first-run accounts and reject a known unsafe legacy admin password."""
    from backend.models.user import User
    from backend.services.auth_service import hash_password, verify_password

    if not db.query(User).first():
        db.add(User(id="u_default", username="default", name="学生"))

    admin_user = db.query(User).filter(User.role == "admin").first()
    if admin_user:
        if runtime_config.environment == "production" and verify_password("admin123", admin_user.password_hash):
            raise RuntimeError(
                "Existing administrator uses the default password. Stop the service and perform password rotation with "
                "scripts/rotate_admin_password.py using ADMIN_PASS before startup."
            )
        return

    admin = User(id="u_admin", username="admin", password_hash=hash_password(runtime_config.admin_pass), name="管理员", role="admin", school_level="高中")
    db.add(admin)
    db.commit()
    logger.info("Initial administrator account created")

@app.on_event("startup")
def startup():
    runtime_config = load_runtime_config()
    init_db()
    db = SessionLocal()
    from backend.services.seed_service import seed_database
    seed_database(db)
    ensure_initial_accounts(db, runtime_config)
    db.close()
    from backend.services.ocr_service import init_ocr_background
    init_ocr_background()
    logger.info("Startup complete")

app.include_router(knowmap.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")
app.include_router(tutor.router, prefix="/api/v1")
app.include_router(learn.router, prefix="/api/v1")
app.include_router(settings.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(referral.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(review.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


# --- Serve compiled frontend (single-port production) ---------------------
# When ``frontend/dist`` exists, mount it so ``/`` returns index.html and
# ``/assets/*`` serves the compiled bundle. Missing dir is not an error (dev
# mode still uses Vite on :5173).
import os as _os
from pathlib import Path as _Path
from fastapi.responses import FileResponse as _FileResponse
from fastapi.staticfiles import StaticFiles as _StaticFiles

_DIST = _Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _DIST.is_dir():
    app.mount("/assets", _StaticFiles(directory=str(_DIST / "assets")), name="assets")

    @app.get("/")
    def _index():
        return _FileResponse(str(_DIST / "index.html"))

    # SPA fallback: any GET that is not an API route falls back to index.html
    from starlette.requests import Request as _Req
    from starlette.responses import Response as _Resp

    @app.middleware("http")
    async def _spa_fallback(request: _Req, call_next):
        resp: _Resp = await call_next(request)
        if (
            resp.status_code == 404
            and request.method == "GET"
            and not request.url.path.startswith(("/api", "/assets", "/health", "/docs", "/openapi"))
        ):
            return _FileResponse(str(_DIST / "index.html"))
        return resp
    logger.info(f"Serving frontend from {_DIST}")
else:
    logger.info("frontend/dist not present; frontend not served from backend")
