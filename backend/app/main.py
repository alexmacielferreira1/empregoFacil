from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.routers import admin, auth, candidates, courses, jobs
from app.seed import seed

settings = get_settings()
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"  # build do React (frontend/dist)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # MVP: cria as tabelas direto. Ao estabilizar o modelo, migrar para Alembic (padrão da Base).
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    yield


app = FastAPI(title="empregoFacil API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, candidates.router, candidates.parceiro_router, courses.router, jobs.router, admin.router):
    app.include_router(r)


# ---------- frontend (SPA) servido pelo mesmo app ----------
if (STATIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str):
    if full_path.startswith("api/"):
        return JSONResponse({"detail": "Não encontrado"}, status_code=404)
    arquivo = STATIC_DIR / full_path
    if full_path and arquivo.is_file() and STATIC_DIR in arquivo.resolve().parents:
        return FileResponse(arquivo)
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse({"app": settings.app_name, "docs": "/docs", "aviso": "Frontend não compilado. Rode build.sh."})
