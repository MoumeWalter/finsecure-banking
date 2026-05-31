"""Tests d'integration des endpoints transactions.

Requiert MongoDB demarre + collection transactions_enriched peuplee.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestListTransactions:
    """GET /api/v1/transactions (liste paginee)."""

    async def test_liste_par_defaut(self, api_client):
        """Liste sans filtre, page 1, taille par defaut."""
        response = await api_client.get("/api/v1/transactions")
        assert response.status_code == 200
        body = response.json()
        assert body["page"] == 1
        assert len(body["items"]) > 0
        assert body["total"] > 0

    async def test_pagination(self, api_client):
        """Deux pages successives renvoient des items differents."""
        page1 = (await api_client.get("/api/v1/transactions?page=1&page_size=5")).json()
        page2 = (await api_client.get("/api/v1/transactions?page=2&page_size=5")).json()
        assert len(page1["items"]) == 5
        assert len(page2["items"]) == 5
        # Aucune transaction n'apparait dans les 2 pages
        ids_p1 = {tx["id_transaction"] for tx in page1["items"]}
        ids_p2 = {tx["id_transaction"] for tx in page2["items"]}
        assert ids_p1.isdisjoint(ids_p2)

    async def test_page_size_max(self, api_client):
        """page_size au-dela de 200 est refuse."""
        response = await api_client.get("/api/v1/transactions?page_size=500")
        assert response.status_code == 422  # validation error

    async def test_filtre_par_fraude(self, api_client):
        """is_fraud=true renvoie uniquement des fraudes."""
        response = await api_client.get(
            "/api/v1/transactions?is_fraud=true&page_size=20"
        )
        assert response.status_code == 200
        body = response.json()
        # Toutes les transactions retournees doivent etre frauduleuses
        for tx in body["items"]:
            assert tx["fraude"]["is_fraud"] is True

    async def test_filtre_par_client(self, api_client):
        """Le filtre id_client renvoie uniquement les tx de ce client."""
        # On utilise le client 1066 qui a 136 transactions dans nos donnees
        response = await api_client.get(
            "/api/v1/transactions?id_client=1066&page_size=10"
        )
        assert response.status_code == 200
        body = response.json()
        for tx in body["items"]:
            assert tx["client"]["id_client"] == 1066


class TestGetTransactionById:
    """GET /api/v1/transactions/{id}."""

    async def test_transaction_inexistante_404(self, api_client):
        """Un ID qui n'existe pas retourne 404."""
        response = await api_client.get("/api/v1/transactions/999999999")
        assert response.status_code == 404
        assert "introuvable" in response.json()["detail"]

    async def test_transaction_existante(self, api_client):
        """Recupere une transaction connue et verifie la structure."""
        # On prend d'abord une transaction quelconque de la liste
        liste = (await api_client.get("/api/v1/transactions?page_size=1")).json()
        if not liste["items"]:
            pytest.skip("Aucune transaction en base")
        id_tx = liste["items"][0]["id_transaction"]

        response = await api_client.get(f"/api/v1/transactions/{id_tx}")
        assert response.status_code == 200
        tx = response.json()
        # Structure attendue (documents enrichis)
        assert tx["id_transaction"] == id_tx
        assert "carte" in tx
        assert "client" in tx
        assert "marchand" in tx
        assert "mcc" in tx
        assert "fraude" in tx
        # Cohérence : id_carte de la transaction doit etre dans carte
        assert tx["carte"]["id_carte"] > 0
