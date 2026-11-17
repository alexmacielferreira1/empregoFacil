import secrets

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import CATEGORIAS, PERGUNTAS, gerar_curriculo
from app.arquivos import TIPOS, categorias_do_texto, extrair_texto, identificar, organizar
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
    resume.origem, resume.usar_arquivo = "voz", False  # o arquivo enviado (se houver) continua guardado
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


# ---------- currículo pronto (arquivo) ----------
def _aplicar_organizado(resume: Resume, conteudo: dict, motor: str) -> None:
    resume.categorias = conteudo.pop("categorias", []) or resume.categorias or []
    resume.conteudo, resume.gerado_por = conteudo, motor
    resume.origem, resume.usar_arquivo, resume.confirmado = "arquivo_atualizado", False, False


@router.post("/curriculo/arquivo", response_model=ResumeOut)
async def enviar_arquivo(
    arquivo: UploadFile = File(...),
    modo: str = Form(..., pattern="^(usar|atualizar)$"),
    categorias: str = Form(""),
    user: User = Depends(candidato_only),
    db: Session = Depends(get_db),
):
    """modo=usar: a empresa recebe o arquivo como está. modo=atualizar: lemos e reorganizamos no modelo do app."""
    dados = await arquivo.read(5 * 1024 * 1024 + 1)
    nome_arq = (arquivo.filename or "curriculo").replace("/", "_")[-150:]
    tipo = identificar(nome_arq, dados)
    prof = get_profile(user, db)
    resume = prof.resume or Resume(candidate_id=prof.id, respostas={}, conteudo={}, categorias=[])
    escolhidas = [c for c in categorias.split(",") if c in CATEGORIAS]

    if modo == "atualizar":
        limitar(f"curriculo:{user.id}", maximo=10, janela_s=86400,
                mensagem="Você já atualizou muitos currículos hoje. Edite o atual ou tente amanhã.")
        conteudo, motor, _ = organizar(user.nome, tipo, dados)
        _aplicar_organizado(resume, conteudo, motor)
        if escolhidas:
            resume.categorias = list(dict.fromkeys(escolhidas + resume.categorias))
    else:
        detectadas = categorias_do_texto(extrair_texto(tipo, dados))
        resume.categorias = list(dict.fromkeys(escolhidas + detectadas))
        if not resume.categorias:
            raise HTTPException(422, "Escolha pelo menos uma área em que você quer trabalhar.")
        if not resume.conteudo:  # mínimo para a empresa ver na lista
            resume.conteudo = {"nome": user.nome, "objetivo": "", "resumo": "Currículo enviado em arquivo.",
                               "experiencias": [], "habilidades": [], "formacao": "", "disponibilidade": ""}
        resume.origem, resume.usar_arquivo, resume.confirmado = "arquivo", True, True
        resume.gerado_por = resume.gerado_por or "arquivo"

    resume.arquivo_nome, resume.arquivo_tipo, resume.arquivo_dados = nome_arq, TIPOS[tipo], dados
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.post("/curriculo/arquivo/atualizar", response_model=ResumeOut)
def atualizar_arquivo_guardado(user: User = Depends(candidato_only), db: Session = Depends(get_db)):
    """Quem escolheu 'usar como está' pode, depois, pedir para melhorar o mesmo arquivo."""
    resume = get_profile(user, db).resume
    if not resume or not resume.arquivo_dados:
        raise HTTPException(404, "Nenhum arquivo enviado.")
    limitar(f"curriculo:{user.id}", maximo=10, janela_s=86400,
            mensagem="Você já atualizou muitos currículos hoje. Edite o atual ou tente amanhã.")
    tipo = next(k for k, v in TIPOS.items() if v == resume.arquivo_tipo)
    conteudo, motor, _ = organizar(user.nome, tipo, resume.arquivo_dados)
    _aplicar_organizado(resume, conteudo, motor)
    db.commit()
    db.refresh(resume)
    return resume


@router.put("/curriculo/modo", response_model=ResumeOut)
def escolher_modo(usar_arquivo: bool, user: User = Depends(candidato_only), db: Session = Depends(get_db)):
    """Troca o que a empresa recebe: o arquivo original ou o currículo do Emprego Fácil."""
    resume = get_profile(user, db).resume
    if not resume:
        raise HTTPException(404, "Você ainda não tem currículo.")
    if usar_arquivo and not resume.arquivo_nome:
        raise HTTPException(422, "Envie um arquivo primeiro.")
    resume.usar_arquivo = usar_arquivo
    db.commit()
    db.refresh(resume)
    return resume


@router.get("/curriculo/arquivo")
def baixar_meu_arquivo(user: User = Depends(candidato_only), db: Session = Depends(get_db)):
    resume = get_profile(user, db).resume
    if not resume or not resume.arquivo_dados:
        raise HTTPException(404, "Nenhum arquivo enviado.")
    return Response(resume.arquivo_dados, media_type=resume.arquivo_tipo,
                    headers={"Content-Disposition": f'inline; filename="{resume.arquivo_nome}"'})


@router.delete("/curriculo/arquivo", response_model=ResumeOut | None)
def apagar_arquivo(user: User = Depends(candidato_only), db: Session = Depends(get_db)):
    prof = get_profile(user, db)
    resume = prof.resume
    if not resume or not resume.arquivo_nome:
        raise HTTPException(404, "Nenhum arquivo enviado.")
    resume.arquivo_nome = resume.arquivo_tipo = resume.arquivo_dados = None
    resume.usar_arquivo = False
    if resume.origem == "arquivo":  # só existia o arquivo: apaga o currículo inteiro
        db.delete(resume)
        db.commit()
        return None
    db.commit()
    db.refresh(resume)
    return resume


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


def nova_senha_provisoria(alvo: User, db: Session) -> dict:
    senha = f"{secrets.randbelow(10**6):06d}"
    alvo.password_hash = hash_password(senha)
    db.commit()
    return {"id": alvo.id, "nome": alvo.nome, "login": alvo.login, "senha_provisoria": senha}


@parceiro_router.post("/candidatos/{user_id}/nova-senha")
def parceiro_nova_senha(user_id: int, user: User = Depends(require_role("parceiro", "admin")), db: Session = Depends(get_db)):
    """O parceiro só pode gerar senha nova para quem ele mesmo cadastrou."""
    alvo = db.get(User, user_id)
    if not alvo or alvo.role != "candidato" or (user.role != "admin" and alvo.criado_por_id != user.id):
        raise HTTPException(404, "Pessoa não encontrada entre os seus cadastros")
    return nova_senha_provisoria(alvo, db)
