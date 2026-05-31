"""Endpoint /health pour le monitoring."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.api.config import get_settings
from src.api.database import get_db_dependency
from src.api.models import HealthCheck

router = APIRouter(tags=["Monitoring"])


@router.get(
    "/health",
    response_model=HealthCheck,
    summary="Sante de l'API et de ses dependances",
)
async def health(
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
) -> HealthCheck:
    """Retourne l'etat de l'API et la connexion MongoDB."""
    settings = get_settings()
    mongo_info: dict = {"connected": False}
    status = "down"
    try:
        # Ping MongoDB
        await db.command("ping")
        # Stats rapides (volumetrie)
        count = await db[settings.mongo_collection].estimated_document_count()
        mongo_info = {
            "connected": True,
            "database": settings.mongo_database,
            "collection": settings.mongo_collection,
            "estimated_documents": count,
        }
        status = "ok"
    except Exception as exc:  # noqa: BLE001
        mongo_info["error"] = str(exc)
        status = "degraded"

    return HealthCheck(
        status=status,
        api_version=settings.app_version,
        mongodb=mongo_info,
    )
