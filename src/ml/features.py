"""Feature engineering pour le modele de detection de fraude.

Ce module centralise la logique d'extraction des features depuis un document
MongoDB ou un dict de requete API. C'est CRUCIAL que la meme logique soit
utilisee au training et a l'inference : sinon le modele recoit des donnees
differemment formatees et les predictions sont mauvaises.

Features selectionnees (7 au total) :
  - amount         : montant de la transaction (float)
  - use_chip       : type de transaction (str categorical)
  - mcc_code       : code Merchant Category Code (int)
  - merchant_state : etat du marchand (str categorical, peut etre null)
  - hour           : heure de la transaction 0-23 (int)
  - current_age    : age du client (float, default a la mediane si null)
  - gender         : genre du client (str categorical, peut etre null)

Note : ce module supporte les 2 conventions de naming MongoDB rencontrees
dans le projet (anglais / francais) pour la robustesse :
  - fraude.labelled OU fraude.is_labellisee
  - marchand.etat OU marchand.state
  - is_fraud bool (True/False) OU str ("Yes"/"No")
  - date_transaction OU date
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

# -----------------------------------------------------------------------------
# Constantes
# -----------------------------------------------------------------------------
FEATURE_COLUMNS = [
    "amount",
    "use_chip",
    "mcc_code",
    "merchant_state",
    "hour",
    "current_age",
    "gender",
]

NUMERICAL_FEATURES = ["amount", "mcc_code", "hour", "current_age"]
CATEGORICAL_FEATURES = ["use_chip", "merchant_state", "gender"]

# Defaults pour les valeurs nulles a l'inference
DEFAULT_HOUR = 12
DEFAULT_AGE = 45.0  # mediane approximative du dataset
DEFAULT_USE_CHIP = "Swipe Transaction"
DEFAULT_MERCHANT_STATE = "UNKNOWN"
DEFAULT_GENDER = "UNKNOWN"


# -----------------------------------------------------------------------------
# Extraction depuis un document MongoDB enrichi (utilise au training)
# -----------------------------------------------------------------------------
def extract_features_from_mongo_doc(doc: dict[str, Any]) -> dict[str, Any]:
    """Extrait les features ML d'un document MongoDB de transaction enrichie.

    Le schema MongoDB attendu est celui de la collection transactions_enriched
    (cf. Phase 3) avec les sous-documents client/carte/marchand/mcc/fraude.

    Supporte les 2 conventions de naming (fr/en) pour la robustesse.

    Returns:
        dict avec les 7 features (peut contenir des None pour les categorielles)
    """
    # Date : preferer date_transaction, fallback sur date
    date_value = doc.get("date_transaction") or doc.get("date")

    if isinstance(date_value, datetime):
        hour = date_value.hour
    elif isinstance(date_value, str):
        try:
            hour = datetime.fromisoformat(date_value.replace("Z", "+00:00")).hour
        except (ValueError, AttributeError):
            hour = DEFAULT_HOUR
    else:
        hour = DEFAULT_HOUR

    client = doc.get("client") or {}
    marchand = doc.get("marchand") or {}
    mcc = doc.get("mcc") or {}

    # Etat marchand : supporter "etat" (FR) et "state" (EN)
    merchant_state = (
        marchand.get("etat")
        or marchand.get("state")
        or DEFAULT_MERCHANT_STATE
    )

    return {
        "amount": float(doc.get("amount") or 0.0),
        "use_chip": doc.get("use_chip") or DEFAULT_USE_CHIP,
        "mcc_code": int(mcc.get("code") or 0),
        "merchant_state": merchant_state,
        "hour": int(hour),
        "current_age": float(client.get("current_age") or DEFAULT_AGE),
        "gender": client.get("gender") or DEFAULT_GENDER,
    }


# -----------------------------------------------------------------------------
# Extraction depuis une requete API (utilise a l'inference)
# -----------------------------------------------------------------------------
def features_from_request(request_data: dict[str, Any]) -> dict[str, Any]:
    """Construit un dict de features depuis le payload d'une requete /predict.

    Applique les valeurs par defaut pour les champs optionnels manquants.
    """
    return {
        "amount": float(request_data.get("amount") or 0.0),
        "use_chip": request_data.get("use_chip") or DEFAULT_USE_CHIP,
        "mcc_code": int(request_data.get("mcc_code") or 0),
        "merchant_state": request_data.get("merchant_state") or DEFAULT_MERCHANT_STATE,
        "hour": int(request_data.get("hour") if request_data.get("hour") is not None else DEFAULT_HOUR),
        "current_age": float(
            request_data.get("current_age") if request_data.get("current_age") is not None else DEFAULT_AGE
        ),
        "gender": request_data.get("gender") or DEFAULT_GENDER,
    }


# -----------------------------------------------------------------------------
# Conversion en DataFrame pour scikit-learn
# -----------------------------------------------------------------------------
def to_dataframe(features: dict[str, Any] | list[dict[str, Any]]) -> pd.DataFrame:
    """Convertit un dict de features (ou une liste) en DataFrame ordonne."""
    if isinstance(features, dict):
        features = [features]
    df = pd.DataFrame(features)
    # S'assurer que toutes les colonnes sont presentes et dans le bon ordre
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df[FEATURE_COLUMNS]


# -----------------------------------------------------------------------------
# Helper : extraction du label depuis le document MongoDB
# -----------------------------------------------------------------------------
def extract_label(doc: dict[str, Any]) -> int | None:
    """Extrait le label (0=non fraude, 1=fraude) depuis le sous-doc fraude.

    Supporte les 2 conventions :
      - fraude.labelled (bool) + fraude.is_fraud (bool True/False)  [actuel]
      - fraude.is_labellisee (bool) + fraude.is_fraud (str "Yes"/"No") [legacy]

    Returns:
        0, 1 ou None si non labellise.
    """
    fraude = doc.get("fraude") or {}

    # Verifier si labellise (les 2 conventions possibles)
    labelled = fraude.get("labelled")
    if labelled is None:
        labelled = fraude.get("is_labellisee")
    if not labelled:
        return None

    # Extraire la valeur (bool ou string)
    is_fraud = fraude.get("is_fraud")

    # Cas 1 : bool
    if is_fraud is True:
        return 1
    if is_fraud is False:
        return 0

    # Cas 2 : string legacy
    if is_fraud == "Yes":
        return 1
    if is_fraud == "No":
        return 0

    return None
