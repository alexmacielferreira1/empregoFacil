from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "empregoFacil"
    environment: str = "development"

    # Banco: SQLite por padrão (teste rápido). Em produção use PostgreSQL
    # (Neon, ShardCloud Database etc.): postgresql://user:senha@host/db
    database_url: str = "sqlite:///./empregofacil.db"

    # Redis é opcional: sem ele o cache/rate-limit funciona em memória.
    redis_url: str | None = None

    secret_key: str = "troque-esta-chave-em-producao-por-uma-bem-longa"
    access_token_minutes: int = 60 * 24 * 7

    # IA (opcional). Sem chave, o currículo é gerado pelo gerador local por regras.
    anthropic_api_key: str | None = None
    ai_model: str = "claude-haiku-5-5"

    admin_login: str = "admin@empregofacil.app"
    admin_password: str = "admin123"
    seed_demo: bool = True

    cors_origins: str = "*"
    port: int = 80
    app_url: str = "https://empregofacil.shardweb.app"  # usado nos links das mensagens

    # ---------- WhatsApp ----------
    # console = só registra no log (padrão, para testes) | meta = WhatsApp Cloud API oficial | zapi = Z-API
    whatsapp_provider: str = "console"
    # Meta (WhatsApp Cloud API)
    whatsapp_token: str | None = None
    whatsapp_phone_number_id: str | None = None
    whatsapp_api_version: str = "v21.0"
    whatsapp_idioma: str = "pt_BR"
    whatsapp_tpl_codigo: str = "empregofacil_codigo"   # modelo de AUTENTICAÇÃO (botão copiar código)
    whatsapp_tpl_vaga: str = "empregofacil_vaga_nova"  # {{1}} nome {{2}} vaga {{3}} bairro {{4}} link
    whatsapp_tpl_status: str = "empregofacil_status"   # {{1}} nome {{2}} vaga {{3}} empresa {{4}} situação
    # Z-API
    zapi_instance: str | None = None
    zapi_token: str | None = None
    zapi_client_token: str | None = None

    # ---------- E-mail (recuperação de senha de empresas) ----------
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None

    # ---------- Avisos ----------
    aviso_raio_km: float = 10
    aviso_vagas_por_dia: int = 2  # máximo de avisos de vaga nova por pessoa por dia

    @property
    def sqlalchemy_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
