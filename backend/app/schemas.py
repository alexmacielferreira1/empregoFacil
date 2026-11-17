from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Orm(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- auth ----------
class RegisterIn(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    login: str = Field(min_length=4, max_length=120, description="Telefone ou e-mail")
    senha: str = Field(min_length=4, max_length=72)
    role: str = Field(pattern="^(candidato|empresa|parceiro)$")
    bairro: str | None = None
    cidade: str | None = None
    razao_social: str | None = None
    cnpj: str | None = None
    consentimento_lgpd: bool = False


class LoginIn(BaseModel):
    login: str
    senha: str


class UserOut(Orm):
    id: int
    nome: str
    login: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- candidato ----------
class ProfileIn(BaseModel):
    nome: str | None = None
    telefone: str | None = None
    cidade: str | None = None
    bairro: str | None = None
    lat: float | None = None
    lng: float | None = None
    disponibilidade: str | None = None
    consentimento_lgpd: bool | None = None


class ProfileOut(Orm):
    id: int
    telefone: str | None
    cidade: str
    bairro: str | None
    lat: float | None
    lng: float | None
    disponibilidade: str | None
    consentimento_lgpd: bool


class ResumeGenerateIn(BaseModel):
    respostas: dict[str, str]


class ResumeUpdateIn(BaseModel):
    conteudo: dict
    confirmado: bool | None = None


class ResumeOut(Orm):
    id: int
    respostas: dict
    conteudo: dict
    categorias: list
    gerado_por: str
    confirmado: bool
    updated_at: datetime


class PartnerCandidateIn(BaseModel):
    nome: str = Field(min_length=2)
    login: str = Field(min_length=4, description="Telefone da pessoa")
    bairro: str | None = None
    cidade: str | None = None
    consentimento_lgpd: bool = Field(description="A pessoa autorizou o cadastro")


# ---------- cursos ----------
class CourseIn(BaseModel):
    titulo: str
    ofertante: str
    categoria: str
    descricao: str | None = None
    modalidade: str = Field(default="presencial", pattern="^(presencial|online)$")
    preco: float = 0
    carga_horaria: int | None = None
    certificado: bool = True
    cidade: str | None = None
    bairro: str | None = None
    horario: str | None = None
    link: str | None = None
    imagem_url: str | None = None
    contato: str | None = None


class CourseOut(Orm):
    id: int
    titulo: str
    ofertante: str
    categoria: str
    descricao: str | None
    modalidade: str
    preco: float
    carga_horaria: int | None
    certificado: bool
    cidade: str | None
    bairro: str | None
    horario: str | None
    link: str | None
    imagem_url: str | None = None
    contato: str | None
    exemplo: bool
    distancia_km: float | None = None


# ---------- vagas ----------
class JobIn(BaseModel):
    titulo: str
    categoria: str
    descricao: str
    salario: str | None = None
    horario: str | None = None
    cidade: str = "Porto Alegre"
    bairro: str | None = None
    vantagens: list[str] = []
    exige_experiencia: bool = False
    com_treinamento: bool = False
    tipo_treinamento: str | None = Field(default=None, pattern="^(antes|junto)$")
    descricao_treinamento: str | None = None
    curso_id: int | None = None
    vagas: int = 1
    status: str = Field(default="aberta", pattern="^(aberta|pausada|encerrada)$")


class JobOut(Orm):
    id: int
    titulo: str
    categoria: str
    descricao: str
    salario: str | None
    horario: str | None
    cidade: str
    bairro: str | None
    vantagens: list
    exige_experiencia: bool
    com_treinamento: bool
    tipo_treinamento: str | None
    descricao_treinamento: str | None
    curso_id: int | None
    vagas: int
    status: str
    exemplo: bool
    created_at: datetime
    empresa: str | None = None
    distancia_km: float | None = None
    combina: bool = False
    ja_candidatou: bool = False
    total_candidatos: int | None = None
    curso: CourseOut | None = None


class ApplicationIn(BaseModel):
    mensagem: str | None = None


class ApplicationStatusIn(BaseModel):
    status: str = Field(pattern="^(enviada|vista|entrevista|contratado|recusada)$")


class ApplicationOut(Orm):
    id: int
    job_id: int
    status: str
    mensagem: str | None
    created_at: datetime
    vaga: str | None = None
    empresa: str | None = None


class ApplicantOut(BaseModel):
    application_id: int
    status: str
    mensagem: str | None
    created_at: datetime
    nome: str
    telefone: str | None
    bairro: str | None
    distancia_km: float | None
    curriculo: dict | None
