"""Tests unitaires du FraudScorer.

Utilise un VRAI mini-modele scikit-learn entraine sur 2 exemples au lieu
d'un MagicMock, car joblib.dump ne supporte pas MagicMock sous Python 3.14
(bug de pickle).
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder, StandardScaler

from src.ml.features import CATEGORICAL_FEATURES, FEATURE_COLUMNS, NUMERICAL_FEATURES
from src.ml.scorer import FraudScorer, _compute_risk_level

pytestmark = pytest.mark.unit


# -----------------------------------------------------------------------------
# _compute_risk_level
# -----------------------------------------------------------------------------
class TestComputeRiskLevel:
    def test_low(self):
        assert _compute_risk_level(0.1) == "LOW"
        assert _compute_risk_level(0.29) == "LOW"

    def test_medium(self):
        assert _compute_risk_level(0.3) == "MEDIUM"
        assert _compute_risk_level(0.5) == "MEDIUM"
        assert _compute_risk_level(0.69) == "MEDIUM"

    def test_high(self):
        assert _compute_risk_level(0.7) == "HIGH"
        assert _compute_risk_level(0.99) == "HIGH"

    def test_extremes(self):
        assert _compute_risk_level(0.0) == "LOW"
        assert _compute_risk_level(1.0) == "HIGH"


# -----------------------------------------------------------------------------
# Fixture : mini-modele sklearn reel (au lieu de MagicMock)
# -----------------------------------------------------------------------------
@pytest.fixture
def fake_model_pkl(tmp_path: Path) -> tuple[Path, Path]:
    """Cree un mini-modele sklearn entraine + metadata pour les tests."""
    # Mini dataset : 4 exemples, 2 fraudes 2 non-fraudes
    X_train = pd.DataFrame(
        [
            {"amount": 10.0, "use_chip": "Chip Transaction", "mcc_code": 5411,
             "merchant_state": "CA", "hour": 12, "current_age": 30.0, "gender": "Male"},
            {"amount": 50.0, "use_chip": "Swipe Transaction", "mcc_code": 5411,
             "merchant_state": "CA", "hour": 14, "current_age": 35.0, "gender": "Female"},
            {"amount": 5000.0, "use_chip": "Online Transaction", "mcc_code": 7995,
             "merchant_state": "NV", "hour": 3, "current_age": 25.0, "gender": "Male"},
            {"amount": 8000.0, "use_chip": "Online Transaction", "mcc_code": 7995,
             "merchant_state": "NV", "hour": 2, "current_age": 22.0, "gender": "Female"},
        ]
    )[FEATURE_COLUMNS]
    y_train = np.array([0, 0, 1, 1])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERICAL_FEATURES),
            (
                "cat",
                OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1),
                CATEGORICAL_FEATURES,
            ),
        ]
    )
    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", RandomForestClassifier(n_estimators=5, random_state=42)),
        ]
    )
    pipeline.fit(X_train, y_train)

    model_path = tmp_path / "fraud_detector.pkl"
    metadata_path = tmp_path / "model_metadata.json"

    joblib.dump(pipeline, model_path)
    metadata_path.write_text(
        json.dumps(
            {
                "model_version": "1.0.0",
                "model_type": "RandomForestClassifier",
                "trained_at": "2026-06-01T00:00:00+00:00",
                "feature_columns": FEATURE_COLUMNS,
                "numerical_features": NUMERICAL_FEATURES,
                "categorical_features": CATEGORICAL_FEATURES,
                "metrics": {"roc_auc": 0.95, "recall_fraud": 0.8},
                "hyperparameters": {},
            }
        )
    )
    return model_path, metadata_path


# -----------------------------------------------------------------------------
# FraudScorer.load
# -----------------------------------------------------------------------------
class TestFraudScorerLoad:
    def test_charge_modele_existant(self, fake_model_pkl):
        model_path, metadata_path = fake_model_pkl
        scorer = FraudScorer(model_path, metadata_path)
        scorer.load()
        assert scorer.is_loaded
        assert scorer.model_version == "1.0.0"
        assert scorer.model_type == "RandomForestClassifier"
        assert scorer.metrics["roc_auc"] == 0.95

    def test_modele_introuvable_pas_d_erreur(self, tmp_path: Path):
        """Si le modele est introuvable, load() ne doit pas crasher."""
        scorer = FraudScorer(tmp_path / "absent.pkl", tmp_path / "absent.json")
        scorer.load()
        assert not scorer.is_loaded

    def test_metadata_introuvable(self, tmp_path: Path, fake_model_pkl):
        """Si seule la metadata est manquante, load() echoue gracieusement."""
        model_path, _ = fake_model_pkl
        scorer = FraudScorer(model_path, tmp_path / "absent.json")
        scorer.load()
        assert not scorer.is_loaded


# -----------------------------------------------------------------------------
# FraudScorer.predict
# -----------------------------------------------------------------------------
class TestFraudScorerPredict:
    def test_prediction_retourne_dict_complet(self, fake_model_pkl):
        model_path, metadata_path = fake_model_pkl
        scorer = FraudScorer(model_path, metadata_path)
        scorer.load()

        result = scorer.predict(
            {
                "amount": 5000.0,
                "use_chip": "Online Transaction",
                "mcc_code": 7995,
                "merchant_state": "NV",
                "hour": 3,
                "current_age": 25.0,
                "gender": "Male",
            }
        )
        # Verifie la structure de la reponse
        assert "is_fraud_predicted" in result
        assert isinstance(result["is_fraud_predicted"], bool)
        assert 0.0 <= result["fraud_probability"] <= 1.0
        assert result["risk_level"] in ("LOW", "MEDIUM", "HIGH")
        assert result["model_version"] == "1.0.0"
        assert "predicted_at" in result
        assert "features_used" in result

    def test_predict_sans_modele_charge_leve_runtime_error(self, tmp_path: Path):
        scorer = FraudScorer(tmp_path / "absent.pkl", tmp_path / "absent.json")
        scorer.load()
        with pytest.raises(RuntimeError, match="non charge"):
            scorer.predict({"amount": 100.0})

    def test_features_used_inclut_les_defaults(self, fake_model_pkl):
        """La reponse doit inclure les features effectivement utilisees (avec defaults)."""
        model_path, metadata_path = fake_model_pkl
        scorer = FraudScorer(model_path, metadata_path)
        scorer.load()

        result = scorer.predict({"amount": 50.0})  # minimal
        features = result["features_used"]
        assert features["amount"] == 50.0
        # Les autres ont recu des defaults
        assert "use_chip" in features
        assert "hour" in features
        assert "current_age" in features
