from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.routers import admin, auth, candidates, courses, jobs
from app.seed import seed

settings = get_settings()
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"  # build do React (frontend/dist)


def adicionar_colunas_novas() -> None:
    """Migração leve do MVP: cria colunas que o modelo tem e o banco ainda não.

    Só ADICIONA colunas que aceitam nulo (nunca remove nem altera). Ao estabilizar o
    modelo, trocar por Alembic (padrão da Base).
    """
    insp = inspect(engine)
    with engine.begin() as conn:
        for tabela in Base.metadata.sorted_tables:
            if not insp.has_table(tabela.name):
                continue
            existentes = {c["name"] for c in insp.get_columns(tabela.name)}
            for col in tabela.columns:
                if col.name not in existentes and col.nullable:
                    tipo = col.type.compile(dialect=engine.dialect)
                    conn.execute(text(f'ALTER TABLE {tabela.name} ADD COLUMN {col.name} {tipo}'))


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    adicionar_colunas_novas()
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

@app.middleware("http")
async def controle_de_cache(request, call_next):
    """API nunca fica em cache (vagas e status mudam a toda hora). Arquivos com hash no nome: cache longo."""
    resposta = await call_next(request)
    caminho = request.url.path
    if caminho.startswith("/api/"):
        resposta.headers["Cache-Control"] = "no-store"
    elif caminho.startswith("/assets/"):
        resposta.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    else:  # index.html e demais arquivos: sempre conferir se há versão nova
        resposta.headers["Cache-Control"] = "no-cache"
    return resposta


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
    if "." in full_path.rsplit("/", 1)[-1]:  # arquivo (imagem etc.) que não existe -> 404, não o app
        return JSONResponse({"detail": "Arquivo não encontrado"}, status_code=404)
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse({"app": settings.app_name, "docs": "/docs", "aviso": "Frontend não compilado. Rode build.sh."})
