from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.ai import CATEGORIAS
from app.database import get_db
from app.geo import coords, distancia_km
from app.models import Course, User
from app.schemas import CourseIn, CourseOut
from app.security import require_role

router = APIRouter(prefix="/api/cursos", tags=["cursos"])


def course_out(c: Course, lat=None, lng=None) -> CourseOut:
    out = CourseOut.model_validate(c)
    out.distancia_km = distancia_km(lat, lng, c.lat, c.lng) if c.modalidade == "presencial" else None
    return out


@router.get("", response_model=list[CourseOut])
def listar(
    categoria: str | None = None,
    gratuito: bool | None = None,
    preco_max: float | None = None,
    modalidade: str | None = None,
    busca: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    bairro: str | None = None,
    db: Session = Depends(get_db),
):
    q = select(Course).where(Course.ativo.is_(True))
    if categoria:
        q = q.where(Course.categoria == categoria)
    if gratuito:
        q = q.where(Course.preco == 0)
    if preco_max is not None:
        q = q.where(Course.preco <= preco_max)
    if modalidade:
        q = q.where(Course.modalidade == modalidade)
    if busca:
        like = f"%{busca}%"
        q = q.where(or_(Course.titulo.ilike(like), Course.descricao.ilike(like), Course.ofertante.ilike(like)))
    if lat is None and bairro:
        lat, lng = coords(bairro)
    itens = [course_out(c, lat, lng) for c in db.scalars(q).all()]
    # online primeiro empatado com perto; sem distância vai pro fim
    itens.sort(key=lambda c: (c.distancia_km if c.distancia_km is not None else (0 if c.modalidade == "online" else 999), c.preco))
    return itens


@router.get("/categorias")
def categorias():
    return [{"id": k, "nome": v} for k, v in CATEGORIAS.items()]


@router.get("/{course_id}", response_model=CourseOut)
def detalhe(course_id: int, db: Session = Depends(get_db)):
    c = db.get(Course, course_id)
    if not c or not c.ativo:
        raise HTTPException(404, "Curso não encontrado")
    return course_out(c)


@router.post("", response_model=CourseOut, status_code=201)
def criar(data: CourseIn, user: User = Depends(require_role("admin", "parceiro", "empresa")), db: Session = Depends(get_db)):
    if data.categoria not in CATEGORIAS:
        raise HTTPException(422, "Categoria inválida")
    c = Course(**data.model_dump(), criado_por_id=user.id)
    c.lat, c.lng = coords(data.bairro or data.cidade)
    db.add(c)
    db.commit()
    return course_out(c)


@router.put("/{course_id}", response_model=CourseOut)
def editar(course_id: int, data: CourseIn, user: User = Depends(require_role("admin", "parceiro", "empresa")),
           db: Session = Depends(get_db)):
    c = db.get(Course, course_id)
    if not c:
        raise HTTPException(404, "Curso não encontrado")
    if user.role != "admin" and c.criado_por_id != user.id:
        raise HTTPException(403, "Só quem cadastrou pode editar")
    for k, v in data.model_dump().items():
        setattr(c, k, v)
    c.lat, c.lng = coords(data.bairro or data.cidade)
    db.commit()
    return course_out(c)


@router.delete("/{course_id}", status_code=204)
def remover(course_id: int, user: User = Depends(require_role("admin", "parceiro", "empresa")), db: Session = Depends(get_db)):
    c = db.get(Course, course_id)
    if not c:
        raise HTTPException(404, "Curso não encontrado")
    if user.role != "admin" and c.criado_por_id != user.id:
        raise HTTPException(403, "Só quem cadastrou pode remover")
    c.ativo = False
    db.commit()
