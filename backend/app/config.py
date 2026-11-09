from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://talentflow_app:talentflow_pass@localhost:5432/talentflow"
    jwt_secret: str = "cambia-esta-clave-en-produccion"
    jwt_algoritmo: str = "HS256"
    jwt_expira_minutos: int = 480
    cors_origins: str = "http://localhost:5176"

    # URL pública del frontend: se usa para los enlaces de los correos (portal, pruebas).
    frontend_url: str = "http://localhost:5176"
    upload_dir: Path = BASE_DIR / "uploads"
    max_cv_mb: int = 5

    # SMTP opcional. Sin smtp_host los correos se guardan en la bandeja como "simulado".
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_usuario: str = ""
    smtp_password: str = ""
    smtp_remitente: str = "TalentFlow <no-responder@talentflow.local>"
    smtp_tls: bool = True

    # Privacidad
    retencion_meses: int = 24
    version_consentimiento: str = "1.0"

    # Pruebas de código
    prueba_codigo_timeout_s: float = 3.0
    spacy_modelo: str = "es_core_news_sm"

    @property
    def cors_lista(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
