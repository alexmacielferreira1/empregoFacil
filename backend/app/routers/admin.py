from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai import CATEGORIAS
from app.config import get_settings
from app.database import get_db
from app.geo import LOCAIS
from app.models import Application, Company, Course, Job, Notificacao, Resume, User
from app.routers.candidates import nova_senha_provisoria
from app.security import require_role

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
def health():
    s = get_settings()
    banco = "postgres" if s.sqlalchemy_url.startswith("postgresql") else "sqlite"
    return {"status": "ok", "app": s.app_name, "versao": "0.2.0", "banco": banco,
            "ia": bool(s.anthropic_api_key), "redis": bool(s.redis_url), "whatsapp": s.whatsapp_provider}


@router.get("/meta")
def meta():
    return {
        "categorias": [{"id": k, "nome": v} for k, v in CATEGORIAS.items()],
        "locais": sorted(LOCAIS.keys()),
        "vantagens": ["Vale-transporte", "Refeição no local", "Vale-alimentação", "Carteira assinada",
                      "Sem experiência", "Horário de meio turno", "Perto de transporte", "Uniforme"],
    }


@router.get("/admin/resumo")
def resumo(user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    def count(model, *where):
        return db.scalar(select(func.count()).select_from(model).where(*where)) or 0

    return {
        "candidatos": count(User, User.role == "candidato"),
        "curriculos": count(Resume),
        "empresas": count(Company),
        "parceiros": count(User, User.role == "parceiro"),
        "vagas_abertas": count(Job, Job.status == "aberta"),
        "vagas_com_treinamento": count(Job, Job.status == "aberta", Job.com_treinamento.is_(True)),
        "cursos": count(Course, Course.ativo.is_(True)),
        "candidaturas": count(Application),
        "contratados": count(Application, Application.status == "contratado"),
        "avisos_whatsapp": count(Notificacao, Notificacao.canal == "whatsapp", Notificacao.status != "falhou"),
        "avisos_falharam": count(Notificacao, Notificacao.status == "falhou"),
    }


@router.get("/admin/usuarios")
def usuarios(user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    rows = db.scalars(select(User).order_by(User.created_at.desc()).limit(200)).all()
    return [{"id": u.id, "nome": u.nome, "login": u.login, "role": u.role, "ativo": u.ativo} for u in rows]


@router.post("/admin/usuarios/{user_id}/nova-senha")
def admin_nova_senha(user_id: int, user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    alvo = db.get(User, user_id)
    if not alvo or alvo.role == "admin":
        raise HTTPException(404, "Usuário não encontrado (a senha do admin vem da variável ADMIN_PASSWORD)")
    return nova_senha_provisoria(alvo, db)


@router.get("/admin/avisos")
def avisos(user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    rows = db.scalars(select(Notificacao).order_by(Notificacao.created_at.desc()).limit(100)).all()
    return [{"id": n.id, "tipo": n.tipo, "canal": n.canal, "destino": n.destino[:-4] + "****" if len(n.destino) > 6 else n.destino,
             "resumo": n.resumo, "status": n.status, "erro": n.erro, "created_at": n.created_at} for n in rows]
