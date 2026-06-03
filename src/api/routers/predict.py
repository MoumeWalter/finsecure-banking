"""Router FastAPI : endpoint de prediction de fraude.

Endpoint :
  POST /api/v1/predict      Predict si une transaction est frauduleuse
  GET  /api/v1/predict/info Retourne les metadonnees du modele charge

Le scorer est charge au demarrage de l'application (cf lifespan dans main.py).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.ml.scorer import get_scorer

router = APIRouter(prefix="/api/v1/predict", tags=["prediction"])


# -----------------------------------------------------------------------------
# Schemas Pydantic
# -----------------------------------------------------------------------------
class PredictRequest(BaseModel):
    """Requete de prediction.

    Seul amount est strictement requis. Les autres champs sont fortement
    recommandes pour une bonne precision, mais des defaults sont appliques
    si manquants.
    """

    amount: float = Field(..., gt=0, description="Montant de la transaction (€)", examples=[123.45])
    use_chip: Literal["Swipe Transaction", "Online Transaction", "Chip Transaction"] | None = Field(
        default=None, description="Type d'authentification (defaut: Swipe Transaction)"
    )
    mcc_code: int | None = Field(default=None, ge=0, description="Code MCC du marchand")
    merchant_state: str | None = Field(
        default=None,
        max_length=10,
        description="Etat du marchand (code US 2 lettres, ex: 'CA')",
    )
    hour: int | None = Field(default=None, ge=0, le=23, description="Heure de la transaction (0-23, defaut: 12)")
    current_age: float | None = Field(default=None, gt=0, lt=120, description="Age du client (defaut: 45)")
    gender: Literal["Male", "Female"] | None = Field(default=None, description="Genre du client")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "amount": 1500.0,
                    "use_chip": "Online Transaction",
                    "mcc_code": 5411,
                    "merchant_state": "CA",
                    "hour": 23,
                    "current_age": 35.0,
                    "gender": "Female",
                }
            ]
        }
    }


class PredictResponse(BaseModel):
    """Reponse de prediction."""

    is_fraud_predicted: bool = Field(..., description="Vrai si la transaction est predite comme frauduleuse")
    fraud_probability: float = Field(..., ge=0, le=1, description="Probabilite de fraude [0..1]")
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        ..., description="Niveau de risque agrege (LOW < 0.3, MEDIUM 0.3-0.7, HIGH >= 0.7)"
    )
    model_version: str = Field(..., description="Version du modele utilise")
    model_type: str = Field(..., description="Type d'algorithme du modele")
    predicted_at: datetime = Field(..., description="Horodatage de la prediction (UTC)")
    features_used: dict = Field(..., description="Features effectivement utilisees (avec defaults appliques)")


class ModelInfoResponse(BaseModel):
    """Informations sur le modele charge."""

    is_loaded: bool
    model_version: str
    model_type: str
    metrics: dict
    feature_columns: list[str]


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@router.post(
    "",
    response_model=PredictResponse,
    summary="Predire si une transaction est frauduleuse",
    description=(
        "Envoie les caracteristiques d'une transaction au modele de scoring "
        "et retourne la probabilite de fraude avec un niveau de risque."
    ),
)
async def predict_fraud(request: PredictRequest) -> PredictResponse:
    scorer = get_scorer()

    if not scorer.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Modele de prediction non charge. "
                "Lancer le training : python -m src.ml.train"
            ),
        )

    try:
        result = scorer.predict(request.model_dump())
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la prediction : {exc}",
        ) from exc

    return PredictResponse(**result)


@router.get(
    "/info",
    response_model=ModelInfoResponse,
    summary="Recuperer les metadonnees du modele charge",
)
async def model_info() -> ModelInfoResponse:
    scorer = get_scorer()
    return ModelInfoResponse(
        is_loaded=scorer.is_loaded,
        model_version=scorer.model_version,
        model_type=scorer.model_type,
        metrics=scorer.metrics,
        feature_columns=scorer._metadata.get("feature_columns", []) if scorer.is_loaded else [],
    )
