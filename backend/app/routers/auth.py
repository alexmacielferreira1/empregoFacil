import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.database import get_db
from app.geo import coords
from app.models import CandidateProfile, Company, PasswordReset, User
from app.notificacoes import enviar_codigo
from app.ratelimit import limitar
from app.schemas import EsqueciIn, LoginIn, RedefinirIn, RegisterIn, TokenOut, UserOut
from app.security import create_token, get_current_user, hash_password, verify_password

CODIGO_MINUTOS = 15
CODIGO_TENTATIVAS = 5

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
            consentimento_lgpd=data.consentimento_lgpd, avisos_whatsapp=data.avisos_whatsapp,
        ))
    elif data.role == "empresa":
        db.add(Company(user_id=user.id, razao_social=data.razao_social, cnpj=data.cnpj,
                       cidade=data.cidade or "Porto Alegre", bairro=data.bairro))
    db.commit()
    return TokenOut(access_token=create_token(user), user=UserOut.model_validate(user))


def _ip(request: Request) -> str:
    return (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "?")).split(",")[0].strip()


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, request: Request, db: Session = Depends(get_db)):
    login_norm = normalizar_login(data.login)
    limitar(f"login:{login_norm}", maximo=10, janela_s=900, mensagem="Muitas tentativas. Espere 15 minutos ou recupere a senha.")
    limitar(f"login-ip:{_ip(request)}", maximo=40, janela_s=900, mensagem="Muitas tentativas. Espere alguns minutos.")
    user = db.scalar(select(User).where(User.login == login_norm))
    if not user or not verify_password(data.senha, user.password_hash):
        raise HTTPException(401, "Telefone/e-mail ou senha incorretos")
    if not user.ativo:
        raise HTTPException(403, "Conta desativada")
    return TokenOut(access_token=create_token(user), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


# ---------- recuperação de senha ----------
RESPOSTA_GENERICA = "Se existir uma conta com esse telefone/e-mail, enviamos um código de 6 números."


@router.post("/esqueci")
def esqueci(data: EsqueciIn, request: Request, db: Session = Depends(get_db)):
    """Sempre responde igual, exista a conta ou não (não revela quem tem cadastro)."""
    login = normalizar_login(data.login)
    limitar(f"esqueci:{login}", maximo=3, janela_s=3600, mensagem="Você já pediu 3 códigos nesta hora. Espere um pouco.")
    limitar(f"esqueci-ip:{_ip(request)}", maximo=10, janela_s=3600, mensagem="Muitos pedidos. Espere um pouco.")
    user = db.scalar(select(User).where(User.login == login))
    canal = "email" if "@" in login else "whatsapp"
    if user and user.ativo:
        db.execute(update(PasswordReset).where(PasswordReset.user_id == user.id, PasswordReset.usado.is_(False))
                   .values(usado=True))  # invalida códigos anteriores
        codigo = f"{secrets.randbelow(10**6):06d}"
        db.add(PasswordReset(user_id=user.id, code_hash=hash_password(codigo), canal=canal,
                             expira_em=datetime.now(timezone.utc) + timedelta(minutes=CODIGO_MINUTOS)))
        db.commit()
        canal = enviar_codigo(db, user, codigo)
    return {"mensagem": RESPOSTA_GENERICA, "canal": canal}


@router.post("/redefinir")
def redefinir(data: RedefinirIn, db: Session = Depends(get_db)):
    erro = HTTPException(400, "Código errado ou vencido. Peça um novo código.")
    user = db.scalar(select(User).where(User.login == normalizar_login(data.login)))
    if not user:
        raise erro
    pedido = db.scalar(select(PasswordReset).where(PasswordReset.user_id == user.id, PasswordReset.usado.is_(False))
                       .order_by(PasswordReset.created_at.desc()))
    if not pedido:
        raise erro
    expira = pedido.expira_em if pedido.expira_em.tzinfo else pedido.expira_em.replace(tzinfo=timezone.utc)
    if expira < datetime.now(timezone.utc) or pedido.tentativas >= CODIGO_TENTATIVAS:
        pedido.usado = True
        db.commit()
        raise erro
    if not verify_password(data.codigo, pedido.code_hash):
        pedido.tentativas += 1
        if pedido.tentativas >= CODIGO_TENTATIVAS:
            pedido.usado = True
        db.commit()
        raise HTTPException(400, f"Código errado. Você ainda tem {max(CODIGO_TENTATIVAS - pedido.tentativas, 0)} tentativa(s).")
    pedido.usado = True
    user.password_hash = hash_password(data.nova_senha)
    db.commit()
    return TokenOut(access_token=create_token(user), user=UserOut.model_validate(user))
