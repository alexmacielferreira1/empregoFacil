from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


ROLES = ("candidato", "empresa", "parceiro", "admin")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    login: Mapped[str] = mapped_column(String(120), unique=True, index=True)  # telefone ou e-mail
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), index=True)
    nome: Mapped[str] = mapped_column(String(120))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_por_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    candidate: Mapped["CandidateProfile | None"] = relationship(back_populates="user", uselist=False)
    company: Mapped["Company | None"] = relationship(back_populates="user", uselist=False)


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    telefone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    cidade: Mapped[str] = mapped_column(String(80), default="Porto Alegre")
    bairro: Mapped[str | None] = mapped_column(String(80), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    disponibilidade: Mapped[str | None] = mapped_column(String(200), nullable=True)
    consentimento_lgpd: Mapped[bool] = mapped_column(Boolean, default=False)
    # Avisos no WhatsApp (opt-in). Nulo em contas antigas = não recebe até a pessoa ligar.
    avisos_whatsapp: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    user: Mapped[User] = relationship(back_populates="candidate")
    resume: Mapped["Resume | None"] = relationship(back_populates="candidate", uselist=False)


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id"), unique=True)
    respostas: Mapped[dict] = mapped_column(JSON, default=dict)  # falas transcritas da entrevista
    conteudo: Mapped[dict] = mapped_column(JSON, default=dict)  # currículo estruturado
    categorias: Mapped[list] = mapped_column(JSON, default=list)
    gerado_por: Mapped[str] = mapped_column(String(20), default="regras")  # "ia" ou "regras"
    confirmado: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    candidate: Mapped[CandidateProfile] = relationship(back_populates="resume")


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    razao_social: Mapped[str] = mapped_column(String(160))
    cnpj: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cidade: Mapped[str] = mapped_column(String(80), default="Porto Alegre")
    bairro: Mapped[str | None] = mapped_column(String(80), nullable=True)
    verificada: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="company")
    jobs: Mapped[list["Job"]] = relationship(back_populates="company")


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    titulo: Mapped[str] = mapped_column(String(160))
    ofertante: Mapped[str] = mapped_column(String(160))
    categoria: Mapped[str] = mapped_column(String(40), index=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    modalidade: Mapped[str] = mapped_column(String(20), default="presencial")  # presencial | online
    preco: Mapped[float] = mapped_column(Float, default=0)
    carga_horaria: Mapped[int | None] = mapped_column(Integer, nullable=True)
    certificado: Mapped[bool] = mapped_column(Boolean, default=True)
    cidade: Mapped[str | None] = mapped_column(String(80), nullable=True)
    bairro: Mapped[str | None] = mapped_column(String(80), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    horario: Mapped[str | None] = mapped_column(String(120), nullable=True)
    link: Mapped[str | None] = mapped_column(String(300), nullable=True)
    imagem_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contato: Mapped[str | None] = mapped_column(String(160), nullable=True)
    exemplo: Mapped[bool] = mapped_column(Boolean, default=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_por_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    titulo: Mapped[str] = mapped_column(String(160))
    categoria: Mapped[str] = mapped_column(String(40), index=True)
    descricao: Mapped[str] = mapped_column(Text)
    salario: Mapped[str | None] = mapped_column(String(80), nullable=True)
    horario: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cidade: Mapped[str] = mapped_column(String(80), default="Porto Alegre")
    bairro: Mapped[str | None] = mapped_column(String(80), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    vantagens: Mapped[list] = mapped_column(JSON, default=list)
    exige_experiencia: Mapped[bool] = mapped_column(Boolean, default=False)
    com_treinamento: Mapped[bool] = mapped_column(Boolean, default=False)
    tipo_treinamento: Mapped[str | None] = mapped_column(String(20), nullable=True)  # antes | junto
    descricao_treinamento: Mapped[str | None] = mapped_column(Text, nullable=True)
    curso_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True)
    vagas: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="aberta")  # aberta | pausada | encerrada
    exemplo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    company: Mapped[Company] = relationship(back_populates="jobs")
    curso: Mapped[Course | None] = relationship()
    applications: Mapped[list["Application"]] = relationship(back_populates="job")


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("job_id", "candidate_id", name="uq_application_job_candidate"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="enviada")  # enviada | vista | entrevista | contratado | recusada
    mensagem: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    job: Mapped[Job] = relationship(back_populates="applications")
    candidate: Mapped[CandidateProfile] = relationship()


class PasswordReset(Base):
    """Código de recuperação de senha. Guardamos só o hash do código."""
    __tablename__ = "password_resets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    code_hash: Mapped[str] = mapped_column(String(200))
    canal: Mapped[str] = mapped_column(String(20))  # whatsapp | email
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    tentativas: Mapped[int] = mapped_column(Integer, default=0)
    usado: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Notificacao(Base):
    """Registro de cada aviso enviado (ou que falhou). Nunca guarda códigos de senha."""
    __tablename__ = "notificacoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    canal: Mapped[str] = mapped_column(String(20))   # whatsapp | email
    tipo: Mapped[str] = mapped_column(String(30), index=True)  # codigo | vaga_nova | status
    destino: Mapped[str] = mapped_column(String(120))
    resumo: Mapped[str] = mapped_column(String(300))
    referencia_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # vaga ou candidatura
    status: Mapped[str] = mapped_column(String(20))  # enviado | falhou | simulado
    erro: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
