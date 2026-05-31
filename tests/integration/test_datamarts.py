"""Tests d'integration des endpoints /api/v1/datamarts."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestMccDatamart:
    """GET /api/v1/datamarts/mcc."""

    async def test_top_mcc_renvoie_liste(self, api_client):
        response = await api_client.get("/api/v1/datamarts/mcc?limit=10")
        assert response.status_code == 200
        results = response.json()
        assert isinstance(results, list)
        assert 1 <= len(results) <= 10

    async def test_top_mcc_trie_par_volume_decroissant(self, api_client):
        response = await api_client.get("/api/v1/datamarts/mcc?limit=5")
        results = response.json()
        if len(results) < 2:
            pytest.skip("Pas assez de MCC pour tester le tri")
        # nb_transactions doit etre decroissant
        counts = [r["nb_transactions"] for r in results]
        assert counts == sorted(counts, reverse=True)

    async def test_top_mcc_grocery_en_premier(self, api_client):
        """D'apres les donnees migrees, Grocery Stores est le top categorie."""
        response = await api_client.get("/api/v1/datamarts/mcc?limit=1")
        results = response.json()
        if not results:
            pytest.skip("Pas de donnees MCC")
        # Le code MCC 5411 = Grocery Stores, Supermarkets
        assert results[0]["code_mcc"] == 5411


class TestCardsDatamart:
    """GET /api/v1/datamarts/cards."""

    async def test_cards_par_defaut(self, api_client):
        response = await api_client.get("/api/v1/datamarts/cards?limit=10")
        assert response.status_code == 200
        cards = response.json()
        assert len(cards) <= 10

    async def test_cards_filtre_min_transactions(self, api_client):
        """min_transactions=100 ne renvoie que les cartes actives."""
        response = await api_client.get(
            "/api/v1/datamarts/cards?min_transactions=100&limit=5"
        )
        cards = response.json()
        for c in cards:
            assert c["nb_transactions"] >= 100

    async def test_cards_tri_par_taux_fraude(self, api_client):
        """Tri par taux_fraude_pct descendant."""
        response = await api_client.get(
            "/api/v1/datamarts/cards?sort_by=taux_fraude_pct&sort_desc=true&min_transactions=100&limit=5"
        )
        cards = response.json()
        if len(cards) < 2:
            pytest.skip("Pas assez de cartes a risque pour tester")
        rates = [c.get("taux_fraude_pct", 0) or 0 for c in cards]
        assert rates == sorted(rates, reverse=True)

    async def test_cards_sort_by_invalide_refuse(self, api_client):
        """Un champ de tri non autorise est rejete par la regex."""
        response = await api_client.get(
            "/api/v1/datamarts/cards?sort_by=injection_attempt"
        )
        assert response.status_code == 422


class TestFraudStats:
    """GET /api/v1/datamarts/fraud-stats."""

    async def test_fraud_stats_structure(self, api_client):
        response = await api_client.get("/api/v1/datamarts/fraud-stats")
        assert response.status_code == 200
        stats = response.json()
        assert "total_transactions" in stats
        assert "nb_fraudes" in stats
        assert "taux_global_pct" in stats
        assert "par_genre" in stats
        assert "par_type_paiement" in stats

    async def test_fraud_stats_coherent(self, api_client):
        """La somme par genre doit egaler le nombre total de fraudes."""
        stats = (await api_client.get("/api/v1/datamarts/fraud-stats")).json()
        if stats["nb_fraudes"] == 0:
            pytest.skip("Pas de fraudes dans le dataset")
        assert sum(stats["par_genre"].values()) == stats["nb_fraudes"]
        assert sum(stats["par_type_paiement"].values()) == stats["nb_fraudes"]

    async def test_fraud_stats_taux_realiste(self, api_client):
        """Le taux global doit etre faible (< 1%) sur notre dataset."""
        stats = (await api_client.get("/api/v1/datamarts/fraud-stats")).json()
        # Sur le dataset Kaggle, le taux est ~0.1%
        assert 0 <= stats["taux_global_pct"] < 1.0

    async def test_fraud_stats_online_majoritaire(self, api_client):
        """Property test : sur notre dataset, les fraudes en ligne dominent (>50%)."""
        stats = (await api_client.get("/api/v1/datamarts/fraud-stats")).json()
        if stats["nb_fraudes"] < 10:
            pytest.skip("Trop peu de fraudes pour conclure")
        online = stats["par_type_paiement"].get("Online Transaction", 0)
        ratio_online = online / stats["nb_fraudes"]
        # Insight business : > 50% des fraudes sont en ligne (on a mesure 91%)
        assert ratio_online > 0.5
