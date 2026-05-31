"""Fixtures pytest partagees.

Conventions :
- `pytestmark` au niveau du fichier ou de la fonction pour marker les tests
- Markers disponibles : unit, integration
- Les fixtures async utilisent pytest-asyncio (mode auto active dans pyproject.toml)
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Configuration des variables d'environnement pour les tests
# (avant l'import de l'app FastAPI, pour que get_settings() prenne les bonnes valeurs)
os.environ.setdefault("MONGO_HOST", "localhost")
os.environ.setdefault("MONGO_PORT", "27017")
os.environ.setdefault("MONGO_USER", "admin")
os.environ.setdefault("MONGO_PASSWORD", "ChangeMeMongo2026")
os.environ.setdefault("MONGO_DATABASE", "finsecure")


@pytest_asyncio.fixture(scope="function")
async def api_client() -> AsyncIterator[AsyncClient]:
    """Client HTTP asynchrone pour tester l'API FastAPI.

    Utilise ASGITransport pour appeler l'app en-process (sans serveur reseau).
    La connexion MongoDB est etablie via le lifespan FastAPI.
    """
    # Import tardif pour que les variables d'environnement soient lues
    from src.api.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Trigger explicite du lifespan (startup/shutdown) via le context manager
        async with app.router.lifespan_context(app):
            yield client


@pytest.fixture(scope="session")
def mongo_running() -> bool:
    """Verifie qu'une instance MongoDB locale est joignable (port 27017).

    Sert a sauter les tests d'integration si MongoDB n'est pas demarre.
    """
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        result = sock.connect_ex(("localhost", 27017))
        return result == 0
    finally:
        sock.close()
