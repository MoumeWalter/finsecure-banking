"""Endpoints des transactions enrichies."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.api.config import get_settings
from src.api.database import get_db_dependency
from src.api.models import TransactionEnriched, TransactionList

router = APIRouter(prefix="/api/v1/transactions", tags=["Transactions"])


@router.get(
    "/{id_transaction}",
    response_model=TransactionEnriched,
    summary="Detail d'une transaction par son ID",
    responses={
        404: {"description": "Transaction introuvable"},
    },
)
async def get_transaction(
    id_transaction: int,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
) -> dict[str, Any]:
    """Retourne une transaction enrichie (avec carte, client, marchand, mcc, fraude)."""
    settings = get_settings()
    doc = await db[settings.mongo_collection].find_one(
        {"id_transaction": id_transaction},
        projection={"_id": 0},
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {id_transaction} introuvable",
        )
    return doc


@router.get(
    "",
    response_model=TransactionList,
    summary="Liste paginee de transactions (avec filtres)",
)
async def list_transactions(
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    page: int = Query(1, ge=1, description="Numero de page (1-indexed)"),
    page_size: int = Query(20, ge=1, le=200),
    id_client: int | None = Query(None, description="Filtrer par client"),
    id_carte: int | None = Query(None, description="Filtrer par carte"),
    code_mcc: int | None = Query(None, description="Filtrer par categorie marchand"),
    is_fraud: bool | None = Query(None, description="Ne montrer que les fraudes (true)"),
    date_from: datetime | None = Query(None, description="Date minimum (ISO)"),
    date_to: datetime | None = Query(None, description="Date maximum (ISO)"),
) -> dict[str, Any]:
    """Retourne une liste paginee de transactions avec filtres optionnels.

    Les filtres sont combines en AND. Pour le filtre is_fraud=true, on tire
    parti de l'index partiel ix_fraude_partial.
    """
    settings = get_settings()
    collection = db[settings.mongo_collection]

    # Construction du filtre Mongo
    query: dict = {}
    if id_client is not None:
        query["client.id_client"] = id_client
    if id_carte is not None:
        query["carte.id_carte"] = id_carte
    if code_mcc is not None:
        query["mcc.code"] = code_mcc
    if is_fraud is True:
        query["fraude.is_fraud"] = True
    elif is_fraud is False:
        query["fraude.is_fraud"] = False
    if date_from or date_to:
        query["date_transaction"] = {}
        if date_from:
            query["date_transaction"]["$gte"] = date_from
        if date_to:
            query["date_transaction"]["$lte"] = date_to

    # Compte total (estime si pas de filtre, exact sinon)
    if not query:
        total = await collection.estimated_document_count()
    else:
        total = await collection.count_documents(query)

    # Pagination + projection (exclut _id)
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
