"""Tests d'integration de l'endpoint /api/v1/predict.

Ces tests utilisent un modele factice charge en memoire via monkeypatch sur
get_scorer(), donc ils tournent SANS avoir besoin du vrai modele entraine.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import joblib
import numpy as np
import pytest

from src.ml import scorer as scorer_module
from src.ml.scorer import FraudScorer

pytestmark = pytest.mark.integration


# -----------------------------------------------------------------------------
# Fixture : charge un modele factice global pour tous les tests du module
# -----------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def fake_loaded_scorer(tmp_path: Path, monkeypatch):
    """Remplace le scorer global par un scorer avec un modele factice charge."""
    # Creer un fake model
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = np.array([[0.2, 0.8]])
    mock_model.predict.return_value = np.array([1])

    model_path = tmp_path / "fraud_detector.pkl"
    metadata_path = tmp_path / "model_metadata.json"
    joblib.dump(mock_model, model_path)
    metadata_path.write_text(
        json.dumps(
            {
                "model_version": "1.0.0-test",
                "model_type": "MockClassifier",
                "feature_columns": ["amount", "use_chip", "mcc_code", "merchant_state", "hour", "current_age", "gender"],
                "metrics": {"roc_auc": 0.99, "recall_fraud": 0.85},
            }
        )
    )

    # Forcer le scorer global a utiliser ce fake
    fake_scorer = FraudScorer(model_path, metadata_path)
    fake_scorer.load()
    monkeypatch.setattr(scorer_module, "_scorer", fake_scorer)
    yield
    monkeypatch.setattr(scorer_module, "_scorer", None)


# -----------------------------------------------------------------------------
# Tests endpoint POST /api/v1/predict
# -----------------------------------------------------------------------------
class TestPredictEndpoint:
    @pytest.mark.asyncio
    async def test_predict_avec_payload_complet(self, api_client):
        response = await api_client.post(
            "/api/v1/predict",
            json={
                "amount": 1500.0,
                "use_chip": "Online Transaction",
                "mcc_code": 5411,
                "merchant_state": "CA",
                "hour": 23,
                "current_age": 35.0,
                "gender": "Female",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_fraud_predicted"] is True
        assert data["fraud_probability"] == 0.8
        assert data["risk_level"] == "HIGH"
        assert data["model_version"] == "1.0.0-test"
        assert "features_used" in data

    @pytest.mark.asyncio
    async def test_predict_avec_payload_minimal(self, api_client):
        """Seul amount est requis, les autres champs doivent recevoir des defaults."""
        response = await api_client.post("/api/v1/predict", json={"amount": 50.0})
        assert response.status_code == 200
        data = response.json()
        assert "fraud_probability" in data
        assert "risk_level" in data

    @pytest.mark.asyncio
    async def test_amount_negatif_rejette(self, api_client):
        response = await api_client.post("/api/v1/predict", json={"amount": -10.0})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_amount_manquant_rejette(self, api_client):
        response = await api_client.post("/api/v1/predict", json={})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_use_chip_invalide_rejette(self, api_client):
        response = await api_client.post(
            "/api/v1/predict",
            json={"amount": 100.0, "use_chip": "Pas Un Type Valide"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_hour_hors_borne_rejette(self, api_client):
        response = await api_client.post(
            "/api/v1/predict",
            json={"amount": 100.0, "hour": 25},
        )
        assert response.status_code == 422


# -----------------------------------------------------------------------------
# Tests endpoint GET /api/v1/predict/info
# -----------------------------------------------------------------------------
class TestPredictInfoEndpoint:
    @pytest.mark.asyncio
    async def test_info_retourne_metadonnees(self, api_client):
        response = await api_client.get("/api/v1/predict/info")
        assert response.status_code == 200
        data = response.json()
        assert data["is_loaded"] is True
        assert data["model_version"] == "1.0.0-test"
        assert data["model_type"] == "MockClassifier"
        assert "metrics" in data
        assert data["metrics"]["roc_auc"] == 0.99
