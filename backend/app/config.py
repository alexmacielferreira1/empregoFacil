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
