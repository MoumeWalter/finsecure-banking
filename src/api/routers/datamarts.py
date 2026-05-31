"""Endpoints datamarts : top MCC, top cartes, stats fraude."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.api.config import get_settings
from src.api.database import get_db_dependency
from src.api.models import CardAggregate, FraudStats, MccAggregate

router = APIRouter(prefix="/api/v1/datamarts", tags=["Datamarts"])


@router.get(
    "/mcc",
    response_model=list[MccAggregate],
    summary="Top categories marchands (par volume de transactions)",
)
async def get_top_mcc(
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    limit: int = Query(10, ge=1, le=109, description="Nombre de categories"),
) -> list[dict[str, Any]]:
    """Retourne le top des MCC depuis la vue v_mcc_aggregates."""
    cursor = db["v_mcc_aggregates"].find({}, projection={"_id": 0}).limit(limit)
    return await cursor.to_list(length=limit)


@router.get(
    "/cards",
    response_model=list[CardAggregate],
    summary="Aggregats par carte (triable, paginable)",
)
async def get_cards_aggregate(
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    limit: int = Query(20, ge=1, le=200),
    sort_by: str = Query(
        "nb_transactions",
        description="Champ de tri",
        pattern="^(nb_transactions|total_amount|nb_fraudes|taux_fraude_pct)$",
    ),
    sort_desc: bool = Query(True, description="Tri descendant"),
    min_transactions: int = Query(
        0, ge=0, description="Filtrer cartes ayant au moins N transactions"
    ),
) -> list[dict[str, Any]]:
    """Retourne le top des cartes depuis la vue v_card_aggregates."""
    query: dict = {}
    if min_transactions > 0:
        query["nb_transactions"] = {"$gte": min_transactions}

    direction = -1 if sort_desc else 1
    cursor = (
        db["v_card_aggregates"]
        .find(query, projection={"_id": 0})
        .sort(sort_by, direction)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


@router.get(
    "/fraud-stats",
    response_model=FraudStats,
    summary="Statistiques globales sur la fraude",
)
async def get_fraud_stats(
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
) -> dict[str, Any]:
    """Aggregation $facet pour stats multi-axes en un seul appel.

    Cette route est la traduction directe de la DEMO 5 du script
    mongo/03_demos_soutenance.js.
    """
    settings = get_settings()
    collection = db[settings.mongo_collection]

    # Total et nombre de fraudes
    total = await collection.estimated_document_count()
    nb_fraudes = await collection.count_documents({"fraude.is_fraud": True})

    # $facet pour les decoupages par axe
    pipeline = [
        {"$match": {"fraude.is_fraud": True}},
        {
            "$facet": {
                "par_genre": [
                    {"$group": {"_id": "$client.gender", "count": {"$sum": 1}}},
                ],
                "par_type_paiement": [
                    {"$group": {"_id": "$use_chip", "count": {"$sum": 1}}},
                ],
            }
        },
    ]
    facets = await collection.aggregate(pipeline).to_list(length=1)
    par_genre: dict[str, int] = {}
    par_type_paiement: dict[str, int] = {}
    if facets:
        for bucket in facets[0].get("par_genre", []):
            key = bucket["_id"] or "Unknown"
            par_genre[key] = bucket["count"]
        for bucket in facets[0].get("par_type_paiement", []):
            key = bucket["_id"] or "Unknown"
            par_type_paiement[key] = bucket["count"]

    return {
        "total_transactions": total,
        "nb_fraudes": nb_fraudes,
        "taux_global_pct": round(100 * nb_fraudes / total, 4) if total else 0.0,
        "par_genre": par_genre,
        "par_type_paiement": par_type_paiement,
    }
