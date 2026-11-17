from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.geo import coords
from app.models import CandidateProfile, Company, User
from app.schemas import LoginIn, RegisterIn, TokenOut, UserOut
from app.security import create_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def normalizar_login(login: str) -> str:
    login = login.strip().lower()
    if "@" not in login:
        login = "".join(ch for ch in login if ch.isdigit())  # telefone: só números
    return login


@router.post("/register", response_model=TokenOut, status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    login = normalizar_login(data.login)
    if len(login) < 4:
        raise HTTPException(422, "Informe um telefone ou e-mail válido")
    if db.scalar(select(User).where(User.login == login)):
        raise HTTPException(409, "Já existe uma conta com esse telefone/e-mail")
    if data.role == "candidato" and not data.consentimento_lgpd:
        raise HTTPException(422, "É preciso aceitar o uso dos dados para criar o currículo")
    if data.role == "empresa" and not data.razao_social:
        raise HTTPException(422, "Informe o nome da empresa")

    user = User(login=login, password_hash=hash_password(data.senha), role=data.role, nome=data.nome.strip())
    db.add(user)
    db.flush()
    if data.role == "candidato":
        lat, lng = coords(data.bairro or data.cidade)
        db.add(CandidateProfile(
            user_id=user.id, telefone=login if "@" not in login else None,
            cidade=data.cidade or "Porto Alegre", bairro=data.bairro, lat=lat, lng=lng,
            consentimento_lgpd=data.consentimento_lgpd,
        ))
    elif data.role == "empresa":
        db.add(Company(user_id=user.id, razao_social=data.razao_social, cnpj=data.cnpj,
                       cidade=data.cidade or "Porto Alegre", bairro=data.bairro))
    db.commit()
    return TokenOut(access_token=create_token(user), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.login == normalizar_login(data.login)))
    if not user or not verify_password(data.senha, user.password_hash):
        raise HTTPException(401, "Telefone/e-mail ou senha incorretos")
    if not user.ativo:
        raise HTTPException(403, "Conta desativada")
    return TokenOut(access_token=create_token(user), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
