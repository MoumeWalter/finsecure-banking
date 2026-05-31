"""Schemas Pydantic pour les requetes et reponses de l'API.

Les classes ici correspondent aux contrats de l'API. FastAPI utilise
ces classes pour :
  - Valider les requetes entrantes
  - Serialiser les reponses sortantes en JSON
  - Generer automatiquement la documentation Swagger
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Sous-objets embeded dans une transaction
# -----------------------------------------------------------------------------
class CarteEmbedded(BaseModel):
    """Informations carte embarquees dans une transaction."""

    id_carte: int
    card_brand: str | None = None
    card_type: str | None = None
    has_chip: bool | None = None
    credit_limit: float | None = None
    card_on_dark_web: bool | None = None


class ClientEmbedded(BaseModel):
    """Informations client embarquees (sans donnees sensibles RGPD)."""

    id_client: int
    current_age: int | None = None
    gender: str | None = None
    credit_score: int | None = None
    num_credit_cards: int | None = None


class MarchandEmbedded(BaseModel):
    """Informations marchand."""

    id_marchand: int
    ville: str | None = None
    etat: str | None = None
    zip: str | None = None


class McEmbedded(BaseModel):
    """Categorie marchand (Merchant Category Code)."""

    code: int
    libelle: str | None = None


class FraudeEmbedded(BaseModel):
    """Etiquette de fraude (peut etre non labellisee)."""

    is_fraud: bool | None = None
    labelled: bool = False


# -----------------------------------------------------------------------------
# Transaction enrichie complete
# -----------------------------------------------------------------------------
class TransactionEnriched(BaseModel):
    """Document MongoDB transaction enrichi avec embedding complet."""

    id_transaction: int
    date_transaction: datetime | None = None
    amount: float | None = None
    use_chip: str | None = None
    situation_date: datetime | None = None
    carte: CarteEmbedded
    client: ClientEmbedded
    marchand: MarchandEmbedded
    mcc: McEmbedded
    fraude: FraudeEmbedded


class TransactionList(BaseModel):
    """Reponse paginee pour la liste des transactions."""

    total: int = Field(description="Nombre total de documents matchant le filtre")
    page: int = Field(description="Page courante (1-indexed)")
    page_size: int
    items: list[TransactionEnriched]


# -----------------------------------------------------------------------------
# Datamarts (vues d'aggregation)
# -----------------------------------------------------------------------------
class CardAggregate(BaseModel):
    """Aggregat par carte."""

    id_carte: int
    nb_transactions: int
    total_amount: float | None = None
    avg_amount: float | None = None
    nb_fraudes: int
    taux_fraude_pct: float | None = None


class MccAggregate(BaseModel):
    """Aggregat par categorie marchand."""

    code_mcc: int
    libelle_mcc: str | None = None
    nb_transactions: int
    total_amount: float | None = None
    avg_amount: float | None = None
    nb_cartes_uniques: int | None = None


class ClientSummary(BaseModel):
    """Synthese d'un client (proche du datamart Oracle)."""

    id_client: int
    nb_transactions: int
    total_amount: float | None = None
    nb_fraudes: int
    nb_cartes_utilisees: int


class FraudStats(BaseModel):
    """Statistiques globales sur la fraude."""

    total_transactions: int
    nb_fraudes: int
    taux_global_pct: float
    par_genre: dict[str, int]
    par_type_paiement: dict[str, int]


# -----------------------------------------------------------------------------
# Reponses utilitaires
# -----------------------------------------------------------------------------
class HealthCheck(BaseModel):
    """Reponse du endpoint /health."""

    status: str = Field(description="ok / degraded / down")
    api_version: str
    mongodb: dict[str, Any]


class ErrorResponse(BaseModel):
    """Reponse d'erreur standardisee."""

    detail: str
