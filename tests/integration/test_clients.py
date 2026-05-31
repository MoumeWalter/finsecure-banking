"""Tests d'integration des endpoints /api/v1/clients."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# Client connu dans nos donnees (validé en demo Phase 3)
CLIENT_AVEC_DONNEES = 1066
CLIENT_INEXISTANT = 999_999


class TestClientTransactions:
    """GET /api/v1/clients/{id}/transactions."""

    async def test_transactions_d_un_client_connu(self, api_client):
        response = await api_client.get(
            f"/api/v1/clients/{CLIENT_AVEC_DONNEES}/transactions?page_size=10"
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] > 0
        for tx in body["items"]:
            assert tx["client"]["id_client"] == CLIENT_AVEC_DONNEES

    async def test_transactions_triees_par_date_desc(self, api_client):
        """Les transactions doivent etre triees par date_transaction desc."""
        response = await api_client.get(
            f"/api/v1/clients/{CLIENT_AVEC_DONNEES}/transactions?page_size=10"
        )
        body = response.json()
        dates = [tx.get("date_transaction") for tx in body["items"] if tx.get("date_transaction")]
        # Si au moins 2 dates : verifier que c'est descendant
        if len(dates) >= 2:
            assert dates == sorted(dates, reverse=True)

    async def test_client_sans_transaction_retourne_liste_vide(self, api_client):
        response = await api_client.get(
            f"/api/v1/clients/{CLIENT_INEXISTANT}/transactions"
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 0
        assert body["items"] == []


class TestClientSummary:
    """GET /api/v1/clients/{id}/summary (aggregation)."""

    async def test_summary_client_connu(self, api_client):
        response = await api_client.get(
            f"/api/v1/clients/{CLIENT_AVEC_DONNEES}/summary"
        )
        assert response.status_code == 200
        summary = response.json()
        assert summary["id_client"] == CLIENT_AVEC_DONNEES
        assert summary["nb_transactions"] > 0
        assert summary["total_amount"] is not None
        assert summary["nb_cartes_utilisees"] >= 1

    async def test_summary_client_inexistant(self, api_client):
        """Un client inexistant retourne une synthese neutre (pas 404)."""
        response = await api_client.get(
            f"/api/v1/clients/{CLIENT_INEXISTANT}/summary"
        )
        assert response.status_code == 200
        summary = response.json()
        assert summary["id_client"] == CLIENT_INEXISTANT
        assert summary["nb_transactions"] == 0
        assert summary["nb_fraudes"] == 0
        assert summary["nb_cartes_utilisees"] == 0

    async def test_summary_coherent_avec_liste(self, api_client):
        """Le compte du summary doit egaler le total de la liste paginée."""
        liste = (
            await api_client.get(
                f"/api/v1/clients/{CLIENT_AVEC_DONNEES}/transactions?page_size=1"
            )
        ).json()
        summary = (
            await api_client.get(
                f"/api/v1/clients/{CLIENT_AVEC_DONNEES}/summary"
            )
        ).json()
        assert liste["total"] == summary["nb_transactions"]
