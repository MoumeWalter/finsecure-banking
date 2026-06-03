"""Application FastAPI principale.

Lancement local :
    uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

Lancement Docker :
    docker compose up -d finsecure_api
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from src.api.config import get_settings
from src.api.database import close_mongo, connect_mongo
from src.api.routers import clients, datamarts, health, predict, transactions
from src.ml.scorer import get_scorer

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("finsecure_api")


# -----------------------------------------------------------------------------
# Lifespan : connect/close MongoDB + load ML model
# -----------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Gere la connexion MongoDB et le chargement du modele ML sur le cycle de vie."""
    logger.info("Demarrage de l'API FinSecure...")
    try:
        await connect_mongo()
    except Exception:
        logger.exception("Impossible de se connecter a MongoDB au demarrage")
        # On laisse l'app demarrer en mode degraded : /health retournera 'down'

    # --- Chargement du modele ML (Phase 10) ---
    logger.info("Chargement du modele de detection de fraude...")
    scorer = get_scorer()
    if scorer.is_loaded:
        logger.info(
            "Modele charge : %s v%s (ROC-AUC=%.4f)",
            scorer.model_type,
            scorer.model_version,
            scorer.metrics.get("roc_auc", 0.0),
        )
    else:
        logger.warning(
            "Modele ML non charge. L'endpoint /api/v1/predict retournera 503. "
            "Lancer 'python -m src.ml.train' pour entrainer le modele."
        )

    yield
    logger.info("Arret de l'API FinSecure...")
    await close_mongo()


# -----------------------------------------------------------------------------
# Application FastAPI
# -----------------------------------------------------------------------------
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS (en dev on autorise tout, a restreindre en prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Routers
# -----------------------------------------------------------------------------
app.include_router(health.router)
app.include_router(transactions.router)
app.include_router(clients.router)
app.include_router(datamarts.router)
app.include_router(predict.router)


# -----------------------------------------------------------------------------
# Page d'accueil HTML
# -----------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root() -> str:
    """Page d'accueil de l'API avec liens utiles."""
    return f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="utf-8">
        <title>{settings.app_name}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                max-width: 720px;
                margin: 60px auto;
                padding: 20px;
                background: #f5f7fa;
                color: #2c3e50;
            }}
            h1 {{ color: #34495e; }}
            .badge {{
                display: inline-block;
                background: #27ae60;
                color: white;
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 0.85em;
            }}
            ul li {{ margin: 8px 0; }}
            code {{
                background: #ecf0f1;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Monaco', monospace;
            }}
            a {{ color: #2980b9; }}
        </style>
    </head>
    <body>
        <h1>{settings.app_name} <span class="badge">v{settings.app_version}</span></h1>
        <p>{settings.app_description}</p>

        <h2>Liens utiles</h2>
        <ul>
            <li><strong><a href="/docs">Swagger UI</a></strong> - Documentation interactive (testable)</li>
            <li><a href="/redoc">ReDoc</a> - Documentation alternative</li>
            <li><a href="/health">/health</a> - Sante de l'API</li>
            <li><a href="/openapi.json">/openapi.json</a> - Specification OpenAPI</li>
        </ul>

        <h2>Endpoints principaux</h2>
        <ul>
            <li><code>GET /api/v1/transactions/{{id}}</code> - Detail d'une transaction</li>
            <li><code>GET /api/v1/transactions</code> - Liste paginee (avec filtres)</li>
            <li><code>GET /api/v1/clients/{{id}}/transactions</code> - Tx d'un client</li>
            <li><code>GET /api/v1/clients/{{id}}/summary</code> - Synthese client</li>
            <li><code>GET /api/v1/datamarts/mcc</code> - Top categories marchands</li>
            <li><code>GET /api/v1/datamarts/cards</code> - Top cartes</li>
            <li><code>GET /api/v1/datamarts/fraud-stats</code> - Stats fraude</li>
            <li><code>POST /api/v1/predict</code> - <strong>Detection de fraude ML</strong> (Phase 10)</li>
            <li><code>GET /api/v1/predict/info</code> - Metadonnees du modele</li>
        </ul>

        <p style="margin-top: 40px; color: #7f8c8d; font-size: 0.9em;">
            Projet certifiant RNCP36739 - M2 Data Engineering EFREI
        </p>
    </body>
    </html>
    """
