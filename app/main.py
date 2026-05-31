import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.database.connection import init_db
from app.routes import auth, api, pages

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚨 ROADSoS AI starting up...")
    os.makedirs("app/static/qr", exist_ok=True)
    os.makedirs("app/static/reports", exist_ok=True)
    os.makedirs("app/static/uploads", exist_ok=True)
    init_db()
    
    # Dynamically alter table for offline_pack_ready
    try:
        from sqlalchemy import text
        from app.database.connection import SessionLocal
        db = SessionLocal()
        db.execute(text("ALTER TABLE users ADD COLUMN offline_pack_ready BOOLEAN DEFAULT 0;"))
        db.commit()
        db.close()
        logger.info("Successfully added offline_pack_ready column to users table.")
    except Exception as e:
        pass

    _seed_demo_data()
    logger.info("✅ ROADSoS AI ready! Visit: http://localhost:8000")
    yield
    logger.info("ROADSoS AI shutting down.")


def _seed_demo_data():
    """Seed a demo user if database is fresh."""
    from app.database.connection import SessionLocal
    from app.models.user import User
    from app.models.medical_profile import MedicalProfile, EmergencyContact
    from app.services.user_service import hash_password

    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            user = User(
                name="Demo User",
                email="demo@roadsos.ai",
                phone="+91 9876543210",
                password_hash=hash_password("demo1234"),
                is_admin=True,
            )
            db.add(user)
            db.flush()

            profile = MedicalProfile(
                user_id=user.id,
                full_name="Demo User",
                age=28,
                blood_group="B+",
                allergies="Penicillin",
                medical_conditions="None",
                medications="None",
                organ_donor=True,
            )
            db.add(profile)

            contact = EmergencyContact(
                user_id=user.id,
                name="Demo Contact",
                relation="Family",
                phone="+91 9123456789",
                is_primary=True,
            )
            db.add(contact)
            db.commit()
            logger.info("✅ Demo user seeded: demo@roadsos.ai / demo1234")
    except Exception as e:
        logger.error(f"Seeding error: {e}")
        db.rollback()
    finally:
        db.close()


app = FastAPI(
    title="ROADSoS AI",
    description="AI-Powered Emergency Response & Disaster Assistance Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(api.router)

templates = Jinja2Templates(directory="app/templates")


@app.exception_handler(404)
async def not_found(request: Request, exc):
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)


@app.exception_handler(500)
async def server_error(request: Request, exc):
    return JSONResponse({"error": "Internal server error"}, status_code=500)


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": "1.0.0"}


@app.get("/manifest.json")
async def manifest():
    return JSONResponse({
        "name": "ROADSoS AI",
        "short_name": "ROADSoS",
        "description": "AI-Powered Emergency Response Platform",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0a0a0a",
        "theme_color": "#dc2626",
        "orientation": "portrait-primary",
        "icons": [
            {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
        "categories": ["health", "emergency", "utilities"],
    })
