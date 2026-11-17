from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai import CATEGORIAS
from app.database import get_db
from app.geo import coords, distancia_km
from app.models import Application, CandidateProfile, Company, Course, Job, User
from app.notificacoes import avisar_status, avisar_vaga_nova
from app.routers.courses import course_out
from app.schemas import ApplicantOut, ApplicationIn, ApplicationOut, ApplicationStatusIn, JobIn, JobOut
from app.security import require_role

router = APIRouter(prefix="/api", tags=["vagas"])


def _perfil(user: User | None, db: Session) -> CandidateProfile | None:
    if not user or user.role != "candidato":
        return None
    return db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))


def job_out(j: Job, prof: CandidateProfile | None = None, lat=None, lng=None, aplicadas: set[int] | None = None) -> JobOut:
    out = JobOut.model_validate(j)
    out.empresa = j.company.razao_social if j.company else None
    if prof and lat is None:
        lat, lng = prof.lat, prof.lng
    out.distancia_km = distancia_km(lat, lng, j.lat, j.lng)
    if prof and prof.resume:
        out.combina = j.categoria in (prof.resume.categorias or [])
    out.ja_candidatou = bool(aplicadas and j.id in aplicadas)
    out.curso = course_out(j.curso) if j.curso else None
    return out


# ---------- público / candidato ----------
@router.get("/vagas", response_model=list[JobOut])
def listar_vagas(
    categoria: str | None = None,
    com_treinamento: bool | None = None,
    sem_experiencia: bool | None = None,
    raio_km: float | None = None,
    busca: str | None = None,
    bairro: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    db: Session = Depends(get_db),
):
    return _listar(db, None, categoria, com_treinamento, sem_experiencia, raio_km, busca, bairro, lat, lng)


@router.get("/candidato/vagas", response_model=list[JobOut])
def vagas_para_mim(
    categoria: str | None = None,
    com_treinamento: bool | None = None,
    sem_experiencia: bool | None = None,
    raio_km: float | None = None,
    busca: str | None = None,
    bairro: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    user: User = Depends(require_role("candidato")),
    db: Session = Depends(get_db),
):
    """Sem bairro/lat: distância a partir do perfil. Com bairro: a partir do bairro escolhido."""
    return _listar(db, user, categoria, com_treinamento, sem_experiencia, raio_km, busca, bairro, lat, lng)


def _listar(db, user, categoria, com_treinamento, sem_experiencia, raio_km, busca, bairro, lat, lng):
    q = select(Job).where(Job.status == "aberta")
    if categoria:
        q = q.where(Job.categoria == categoria)
    if com_treinamento:
        q = q.where(Job.com_treinamento.is_(True))
    if sem_experiencia:
        q = q.where(Job.exige_experiencia.is_(False))
    if busca:
        like = f"%{busca}%"
        q = q.where(or_(Job.titulo.ilike(like), Job.descricao.ilike(like)))
    prof = _perfil(user, db)
    if lat is None and bairro:
        lat, lng = coords(bairro)
    aplicadas = set()
    if prof:
        aplicadas = set(db.scalars(select(Application.job_id).where(Application.candidate_id == prof.id)).all())
    itens = [job_out(j, prof, lat, lng, aplicadas) for j in db.scalars(q).all()]
    if raio_km:
        itens = [i for i in itens if i.distancia_km is not None and i.distancia_km <= raio_km]
    itens.sort(key=lambda i: (not i.combina, i.distancia_km if i.distancia_km is not None else 999))
    return itens


@router.get("/vagas/{job_id}", response_model=JobOut)
def detalhe_vaga(job_id: int, db: Session = Depends(get_db)):
    j = db.get(Job, job_id)
    if not j:
        raise HTTPException(404, "Vaga não encontrada")
    return job_out(j)


@router.post("/vagas/{job_id}/candidatar", response_model=ApplicationOut, status_code=201)
def candidatar(job_id: int, data: ApplicationIn | None = None, user: User = Depends(require_role("candidato")),
               db: Session = Depends(get_db)):
    j = db.get(Job, job_id)
    if not j or j.status != "aberta":
        raise HTTPException(404, "Vaga não está aberta")
    prof = _perfil(user, db)
    if not prof or not prof.resume:
        raise HTTPException(422, "Monte seu currículo antes de se candidatar")
    app_ = Application(job_id=j.id, candidate_id=prof.id, mensagem=data.mensagem if data else None)
    db.add(app_)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Você já se candidatou a esta vaga")
    out = ApplicationOut.model_validate(app_)
    out.vaga, out.empresa = j.titulo, j.company.razao_social
    return out


@router.get("/candidato/candidaturas", response_model=list[ApplicationOut])
def minhas_candidaturas(user: User = Depends(require_role("candidato")), db: Session = Depends(get_db)):
    prof = _perfil(user, db)
    if not prof:
        return []
    apps = db.scalars(select(Application).where(Application.candidate_id == prof.id).order_by(Application.created_at.desc())).all()
    out = []
    for a in apps:
        o = ApplicationOut.model_validate(a)
        o.vaga, o.empresa = a.job.titulo, a.job.company.razao_social
        out.append(o)
    return out


@router.get("/candidato/cursos-sugeridos")
def cursos_sugeridos(user: User = Depends(require_role("candidato")), db: Session = Depends(get_db)):
    """Cursos nas áreas do currículo + cursos ligados a vagas com treinamento."""
    prof = _perfil(user, db)
    cats = (prof.resume.categorias if prof and prof.resume else []) or []
    q = select(Course).where(Course.ativo.is_(True))
    if cats:
        q = q.where(Course.categoria.in_(cats))
    cursos = [course_out(c, prof.lat if prof else None, prof.lng if prof else None) for c in db.scalars(q).all()]
    ligados = set(db.scalars(select(Job.curso_id).where(Job.status == "aberta", Job.curso_id.is_not(None))).all())
    cursos.sort(key=lambda c: (c.id not in ligados, c.preco, c.distancia_km if c.distancia_km is not None else 0))
    return [dict(c.model_dump(), abre_vaga=c.id in ligados) for c in cursos[:8]]


# ---------- empresa ----------
empresa = require_role("empresa")


def _company(user: User, db: Session) -> Company:
    c = db.scalar(select(Company).where(Company.user_id == user.id))
    if not c:
        raise HTTPException(404, "Cadastro da empresa não encontrado")
    return c


def _validar(data: JobIn, db: Session):
    if data.categoria not in CATEGORIAS:
        raise HTTPException(422, "Categoria inválida")
    if data.curso_id and not db.get(Course, data.curso_id):
        raise HTTPException(422, "Curso vinculado não existe")
    if data.com_treinamento and not data.tipo_treinamento:
        raise HTTPException(422, "Diga se o treinamento é antes ou junto com o trabalho")


@router.get("/empresa/vagas", response_model=list[JobOut])
def minhas_vagas(user: User = Depends(empresa), db: Session = Depends(get_db)):
    comp = _company(user, db)
    vagas = db.scalars(select(Job).where(Job.company_id == comp.id).order_by(Job.created_at.desc())).all()
    contagem = dict(db.execute(select(Application.job_id, func.count()).where(
        Application.job_id.in_([v.id for v in vagas] or [0])).group_by(Application.job_id)).all())
    out = []
    for v in vagas:
        o = job_out(v)
        o.total_candidatos = contagem.get(v.id, 0)
        out.append(o)
    return out


@router.post("/empresa/vagas", response_model=JobOut, status_code=201)
def criar_vaga(data: JobIn, tarefas: BackgroundTasks, user: User = Depends(empresa), db: Session = Depends(get_db)):
    _validar(data, db)
    comp = _company(user, db)
    j = Job(**data.model_dump(), company_id=comp.id)
    j.lat, j.lng = coords(data.bairro or data.cidade)
    db.add(j)
    db.commit()
    db.refresh(j)
    if j.status == "aberta":
        tarefas.add_task(avisar_vaga_nova, j.id)
    return job_out(j)


@router.put("/empresa/vagas/{job_id}", response_model=JobOut)
def editar_vaga(job_id: int, data: JobIn, tarefas: BackgroundTasks, user: User = Depends(empresa), db: Session = Depends(get_db)):
    comp = _company(user, db)
    j = db.get(Job, job_id)
    if not j or j.company_id != comp.id:
        raise HTTPException(404, "Vaga não encontrada")
    _validar(data, db)
    if j.status != "aberta" and data.status == "aberta":
        tarefas.add_task(avisar_vaga_nova, j.id)  # reaberta: avisa (quem já foi avisado não recebe de novo)
    for k, v in data.model_dump().items():
        setattr(j, k, v)
    j.lat, j.lng = coords(data.bairro or data.cidade)
    db.commit()
    return job_out(j)


@router.get("/empresa/vagas/{job_id}/candidatos", response_model=list[ApplicantOut])
def candidatos_da_vaga(job_id: int, user: User = Depends(empresa), db: Session = Depends(get_db)):
    comp = _company(user, db)
    j = db.get(Job, job_id)
    if not j or j.company_id != comp.id:
        raise HTTPException(404, "Vaga não encontrada")
    out = []
    for a in sorted(j.applications, key=lambda a: a.created_at, reverse=True):
        p = a.candidate
        if a.status == "enviada":
            a.status = "vista"
        out.append(ApplicantOut(
            application_id=a.id, status=a.status, mensagem=a.mensagem, created_at=a.created_at,
            nome=p.user.nome, telefone=p.telefone, bairro=p.bairro,  # endereço exato nunca é exposto
            distancia_km=distancia_km(p.lat, p.lng, j.lat, j.lng),
            curriculo=p.resume.conteudo if p.resume else None,
            arquivo_nome=p.resume.arquivo_nome if p.resume else None,
            usar_arquivo=bool(p.resume and p.resume.usar_arquivo and p.resume.arquivo_nome),
        ))
    db.commit()
    return out


@router.get("/empresa/candidaturas/{app_id}/arquivo")
def baixar_curriculo_candidato(app_id: int, user: User = Depends(empresa), db: Session = Depends(get_db)):
    """A empresa só baixa o arquivo de quem se candidatou a uma vaga DELA."""
    comp = _company(user, db)
    a = db.get(Application, app_id)
    if not a or a.job.company_id != comp.id or not a.candidate.resume or not a.candidate.resume.arquivo_dados:
        raise HTTPException(404, "Arquivo não encontrado")
    r = a.candidate.resume
    return Response(r.arquivo_dados, media_type=r.arquivo_tipo,
                    headers={"Content-Disposition": f'inline; filename="{r.arquivo_nome}"'})


@router.put("/empresa/candidaturas/{app_id}", response_model=ApplicationOut)
def mudar_status(app_id: int, data: ApplicationStatusIn, tarefas: BackgroundTasks, user: User = Depends(empresa),
                 db: Session = Depends(get_db)):
    comp = _company(user, db)
    a = db.get(Application, app_id)
    if not a or a.job.company_id != comp.id:
        raise HTTPException(404, "Candidatura não encontrada")
    mudou = a.status != data.status
    a.status = data.status
    db.commit()
    if mudou and data.status in ("entrevista", "contratado", "recusada"):
        tarefas.add_task(avisar_status, a.id)
    o = ApplicationOut.model_validate(a)
    o.vaga, o.empresa = a.job.titulo, comp.razao_social
    return o
