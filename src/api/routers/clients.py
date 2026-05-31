"""Endpoints clients : transactions et synthese."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.api.config import get_settings
from src.api.database import get_db_dependency
from src.api.models import ClientSummary, TransactionList

router = APIRouter(prefix="/api/v1/clients", tags=["Clients"])


@router.get(
    "/{id_client}/transactions",
    response_model=TransactionList,
    summary="Toutes les transactions d'un client (paginees, triees par date desc)",
)
async def get_client_transactions(
    id_client: int,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
) -> dict[str, Any]:
    """Retourne les transactions d'un client. Utilise l'index composite ix_client_date."""
    settings = get_settings()
    collection = db[settings.mongo_collection]

    query = {"client.id_client": id_client}
    total = await collection.count_documents(query)

    skip = (page - 1) * page_size
    cursor = (
        collection.find(query, projection={"_id": 0})
        .sort("date_transaction", -1)
        .skip(skip)
        .limit(page_size)
    )
    items = await cursor.to_list(length=page_size)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


@router.get(
    "/{id_client}/summary",
    response_model=ClientSummary,
    summary="Synthese aggrégée d'un client",
)
async def get_client_summary(
    id_client: int,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
) -> dict[str, Any]:
    """Aggregation MongoDB pour synthetiser l'activite d'un client."""
    settings = get_settings()
    collection = db[settings.mongo_collection]

    pipeline = [
        {"$match": {"client.id_client": id_client}},
        {
            "$group": {
                "_id": "$client.id_client",
                "nb_transactions": {"$sum": 1},
                "total_amount": {"$sum": "$amount"},
                "nb_fraudes": {
                    "$sum": {
                        "$cond": [{"$eq": ["$fraude.is_fraud", True]}, 1, 0]
                    }
                },
                "cartes_uniques": {"$addToSet": "$carte.id_carte"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "id_client": "$_id",
                "nb_transactions": 1,
                "total_amount": {"$round": ["$total_amount", 2]},
                "nb_fraudes": 1,
                "nb_cartes_utilisees": {"$size": "$cartes_uniques"},
            }
        },
    ]

    results = await collection.aggregate(pipeline).to_list(length=1)
    if not results:
        # Client sans transaction : retour neutre
        return {
            "id_client": id_client,
            "nb_transactions": 0,
            "total_amount": 0.0,
            "nb_fraudes": 0,
            "nb_cartes_utilisees": 0,
        }
    return results[0]
