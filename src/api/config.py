"""Configuration de l'API FastAPI via Pydantic Settings.

Les variables sont lues depuis l'environnement (ou .env) avec validation
automatique des types. Pattern recommande pour les apps FastAPI en prod.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration centralisee de l'API."""

    # Application
    app_name: str = "FinSecure Banking API"
    app_version: str = "0.1.0"
    app_description: str = (
        "API REST pour exposer les datamarts et donnees de la plateforme "
        "FinSecure Banking. Sert l'analytique et le scoring temps reel."
    )
    debug: bool = Field(default=False, description="Mode debug FastAPI")

    # MongoDB (source principale de l'API)
    mongo_host: str = Field(default="mongo_db", description="Hostname MongoDB")
    mongo_port: int = Field(default=27017, description="Port MongoDB")
    mongo_user: str = Field(default="admin")
    mongo_password: str = Field(default="ChangeMeMongo2026")
    mongo_database: str = Field(default="finsecure")
    mongo_collection: str = Field(default="transactions_enriched")

    # Pagination par defaut
    default_page_size: int = Field(default=20, ge=1, le=200)
    max_page_size: int = Field(default=200, ge=1, le=1000)

    # CORS (en V2 affiner les origins)
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignorer les variables non declarees (ORACLE_*, etc.)
    )

    @property
    def mongo_uri(self) -> str:
        """Construit l'URI MongoDB."""
        return (
            f"mongodb://{self.mongo_user}:{self.mongo_password}"
            f"@{self.mongo_host}:{self.mongo_port}/admin"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton de la config (lru_cache). Permet l'injection FastAPI."""
    return Settings()
