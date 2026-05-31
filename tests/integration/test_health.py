"""Tests d'integration de l'endpoint /health.

Requiert MongoDB demarre sur localhost:27017.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_root_renvoie_html(api_client):
    """La page d'accueil retourne du HTML lisible."""
    response = await api_client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "FinSecure Banking" in response.text


async def test_docs_endpoint_swagger_disponible(api_client):
    """Swagger UI est servie sur /docs."""
    response = await api_client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower()


async def test_openapi_json_valide(api_client):
    """Le schema OpenAPI est genere et accessible."""
    response = await api_client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert spec["info"]["title"] == "FinSecure Banking API"
    # Verifie qu'au moins nos endpoints sont declares
    paths = set(spec["paths"].keys())
    assert "/health" in paths
    assert "/api/v1/transactions/{id_transaction}" in paths


async def test_health_renvoie_ok(api_client):
    """Sante de l'API : MongoDB joignable, > 0 documents."""
    response = await api_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mongodb"]["connected"] is True
    assert body["mongodb"]["estimated_documents"] > 0


async def test_health_donne_la_version(api_client):
    response = await api_client.get("/health")
    body = response.json()
    assert "api_version" in body
    assert body["api_version"]  # non-vide
