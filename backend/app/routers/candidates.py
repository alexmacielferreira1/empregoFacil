import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import PERGUNTAS, gerar_curriculo
from app.database import get_db
from app.geo import coords
from app.models import CandidateProfile, Resume, User
from app.ratelimit import limitar
from app.routers.auth import normalizar_login
from app.schemas import PartnerCandidateIn, ProfileIn, ProfileOut, ResumeGenerateIn, ResumeOut, ResumeUpdateIn
from app.security import hash_password, require_role

router = APIRouter(prefix="/api/candidato", tags=["candidato"])
candidato_only = require_role("candidato")


def get_profile(user: User, db: Session) -> CandidateProfile:
    prof = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    if not prof:
        prof = CandidateProfile(user_id=user.id)
        db.add(prof)
        db.commit()
    return prof


@router.get("/perfil", response_model=ProfileOut)
def ler_perfil(user: User = Depends(candidato_only), db: Session = Depends(get_db)):
    return get_profile(user, db)


@router.put("/perfil", response_model=ProfileOut)
def salvar_perfil(data: ProfileIn, user: User = Depends(candidato_only), db: Session = Depends(get_db)):
    prof = get_profile(user, db)
    campos = data.model_dump(exclude_unset=True)
    if "nome" in campos and campos["nome"]:
        user.nome = campos.pop("nome").strip()
    else:
        campos.pop("nome", None)
    for k, v in campos.items():
        setattr(prof, k, v)
    if ("bairro" in campos or "cidade" in campos) and "lat" not in campos:
        prof.lat, prof.lng = coords(prof.bairro or prof.cidade)
    db.commit()
    return prof


@router.get("/entrevista/perguntas")
def perguntas():
    return PERGUNTAS


@router.get("/curriculo", response_model=ResumeOut | None)
def ler_curriculo(user: User = Depends(candidato_only), db: Session = Depends(get_db)):
    return get_profile(user, db).resume


@router.post("/curriculo/gerar", response_model=ResumeOut)
def gerar(data: ResumeGenerateIn, user: User = Depends(candidato_only), db: Session = Depends(get_db)):
    respostas = {k: v.strip() for k, v in data.respostas.items() if v and v.strip()}
    if not respostas:
        raise HTTPException(422, "Responda pelo menos uma pergunta")
    limitar(f"curriculo:{user.id}", maximo=10, janela_s=86400,
            mensagem="Você já gerou muitos currículos hoje. Edite o atual ou tente amanhã.")
    prof = get_profile(user, db)
    conteudo, motor = gerar_curriculo(user.nome, respostas)
    categorias = conteudo.pop("categorias", [])
    if conteudo.get("disponibilidade") and not prof.disponibilidade:
        prof.disponibilidade = conteudo["disponibilidade"][:200]
    resume = prof.resume or Resume(candidate_id=prof.id)
    resume.respostas, resume.conteudo, resume.categorias = respostas, conteudo, categorias
    resume.gerado_por, resume.confirmado = motor, False
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.put("/curriculo", response_model=ResumeOut)
def editar(data: ResumeUpdateIn, user: User = Depends(candidato_only), db: Session = Depends(get_db)):
    prof = get_profile(user, db)
    if not prof.resume:
        raise HTTPException(404, "Faça a entrevista primeiro")
    conteudo = dict(data.conteudo)
    if "categorias" in conteudo:
        prof.resume.categorias = conteudo.pop("categorias")
    prof.resume.conteudo = conteudo
    if data.confirmado is not None:
        prof.resume.confirmado = data.confirmado
    db.commit()
    db.refresh(prof.resume)
    return prof.resume


# ---------- parceiro social cadastra por alguém ----------
parceiro_router = APIRouter(prefix="/api/parceiro", tags=["parceiro"])


@parceiro_router.post("/candidatos", status_code=201)
def cadastrar_por_alguem(data: PartnerCandidateIn, user: User = Depends(require_role("parceiro", "admin")),
                         db: Session = Depends(get_db)):
    if not data.consentimento_lgpd:
        raise HTTPException(422, "A pessoa precisa autorizar o cadastro")
    login = normalizar_login(data.login)
    if db.scalar(select(User).where(User.login == login)):
        raise HTTPException(409, "Essa pessoa já tem conta")
    senha = f"{secrets.randbelow(10**6):06d}"
    novo = User(login=login, password_hash=hash_password(senha), role="candidato", nome=data.nome.strip(),
                criado_por_id=user.id)
    db.add(novo)
    db.flush()
    lat, lng = coords(data.bairro or data.cidade)
    db.add(CandidateProfile(user_id=novo.id, telefone=login, cidade=data.cidade or "Porto Alegre",
                            bairro=data.bairro, lat=lat, lng=lng, consentimento_lgpd=True))
    db.commit()
    return {"id": novo.id, "nome": novo.nome, "login": login, "senha_provisoria": senha}


@parceiro_router.get("/candidatos")
def meus_cadastrados(user: User = Depends(require_role("parceiro", "admin")), db: Session = Depends(get_db)):
    pessoas = db.scalars(select(User).where(User.criado_por_id == user.id).order_by(User.created_at.desc())).all()
    out = []
    for p in pessoas:
        prof = p.candidate
        out.append({"id": p.id, "nome": p.nome, "login": p.login, "bairro": prof.bairro if prof else None,
                    "tem_curriculo": bool(prof and prof.resume)})
    return out
