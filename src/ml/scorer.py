"""Wrapper de scoring : charge le modele au demarrage et expose predict().

Ce module est importe par l'API FastAPI au demarrage. Il :
  - Charge le modele depuis models/fraud_detector.pkl
  - Charge les metadonnees depuis models/model_metadata.json
  - Expose une fonction predict() qui prend un dict de features et retourne
    un dict standardise (is_fraud_predicted, fraud_probability, risk_level)

Si le modele n'est pas trouve, l'API peut quand meme demarrer mais l'endpoint
/predict retourne une 503.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib

from src.ml.features import features_from_request, to_dataframe

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Seuils de classification
# -----------------------------------------------------------------------------
RISK_LOW_THRESHOLD = 0.3
RISK_HIGH_THRESHOLD = 0.7


def _compute_risk_level(probability: float) -> str:
    if probability < RISK_LOW_THRESHOLD:
        return "LOW"
    if probability < RISK_HIGH_THRESHOLD:
        return "MEDIUM"
    return "HIGH"


# -----------------------------------------------------------------------------
# FraudScorer
# -----------------------------------------------------------------------------
class FraudScorer:
    """Charge le modele et fournit des predictions."""

    def __init__(self, model_path: Path, metadata_path: Path):
        self.model_path = model_path
        self.metadata_path = metadata_path
        self._model = None
        self._metadata: dict[str, Any] = {}
        self._loaded = False

    def load(self) -> None:
        """Charge le modele et les metadonnees depuis le disque."""
        if not self.model_path.exists():
            logger.warning("Modele introuvable : %s", self.model_path)
            return
        if not self.metadata_path.exists():
            logger.warning("Metadonnees introuvables : %s", self.metadata_path)
            return

        try:
            self._model = joblib.load(self.model_path)
            self._metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            self._loaded = True
            logger.info(
                "Modele charge : version=%s, type=%s, ROC-AUC=%.4f",
                self._metadata.get("model_version"),
                self._metadata.get("model_type"),
                self._metadata.get("metrics", {}).get("roc_auc", 0.0),
            )
        except Exception as exc:
            logger.error("Echec du chargement du modele : %s", exc)
            self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def model_version(self) -> str:
        return self._metadata.get("model_version", "unknown")

    @property
    def model_type(self) -> str:
        return self._metadata.get("model_type", "unknown")

    @property
    def metrics(self) -> dict[str, Any]:
        return self._metadata.get("metrics", {})

    def predict(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Effectue une prediction sur une transaction.

        Args:
            request_data: dict avec les champs amount, use_chip, mcc_code, etc.

        Returns:
            dict avec is_fraud_predicted, fraud_probability, risk_level,
            model_version, model_type, predicted_at.

        Raises:
            RuntimeError: si le modele n'est pas charge.
        """
        if not self._loaded or self._model is None:
            raise RuntimeError("Modele non charge. Lancez 'python -m src.ml.train' d'abord.")

        features = features_from_request(request_data)
        df = to_dataframe(features)

        # predict_proba retourne [[proba_classe_0, proba_classe_1]]
        proba_fraud = float(self._model.predict_proba(df)[0, 1])
        is_fraud = bool(self._model.predict(df)[0])
        risk_level = _compute_risk_level(proba_fraud)

        return {
            "is_fraud_predicted": is_fraud,
            "fraud_probability": round(proba_fraud, 4),
            "risk_level": risk_level,
            "model_version": self.model_version,
            "model_type": self.model_type,
            "predicted_at": datetime.now(timezone.utc).isoformat(),
            "features_used": features,
        }


# -----------------------------------------------------------------------------
# Singleton global (charge au demarrage de l'API)
# -----------------------------------------------------------------------------
_scorer: FraudScorer | None = None


def get_scorer(model_dir: Path | None = None) -> FraudScorer:
    """Retourne le scorer singleton, le chargeant si necessaire."""
    global _scorer
    if _scorer is None:
        base_dir = model_dir or Path("models")
        _scorer = FraudScorer(
            model_path=base_dir / "fraud_detector.pkl",
            metadata_path=base_dir / "model_metadata.json",
        )
        _scorer.load()
    return _scorer


def reset_scorer() -> None:
    """Reset le singleton (utilise en test)."""
    global _scorer
    _scorer = None
