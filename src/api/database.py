"""Connexion MongoDB asynchrone via motor.

Pattern : un client global cree au demarrage de l'app (lifespan FastAPI),
ferme proprement a l'arret. Les routes accedent au client via une dependance.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from src.api.config import get_settings

logger = logging.getLogger(__name__)


# Client MongoDB global (initialise dans lifespan main.py)
_client: AsyncIOMotorClient | None = None


async def connect_mongo() -> None:
    """Initialise la connexion MongoDB au demarrage."""
    global _client
    settings = get_settings()
    logger.info("Connexion a MongoDB %s:%d", settings.mongo_host, settings.mongo_port)
    _client = AsyncIOMotorClient(
        settings.mongo_uri,
        serverSelectionTimeoutMS=5000,
    )
    # Force la verification immediate
    await _client.admin.command("ping")
    logger.info("Connexion MongoDB etablie")


async def close_mongo() -> None:
    """Ferme la connexion MongoDB a l'arret."""
    global _client
    if _client is not None:
        logger.info("Fermeture de la connexion MongoDB")
        _client.close()
        _client = None


def get_database() -> AsyncIOMotorDatabase:
    """Dependance FastAPI : retourne la base MongoDB."""
    if _client is None:
        raise RuntimeError("MongoDB client n'est pas initialise")
    settings = get_settings()
    return _client[settings.mongo_database]


async def get_db_dependency() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Generateur pour `Depends(get_db_dependency)` dans les routes."""
    yield get_database()
