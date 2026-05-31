"""Migration des donnees Oracle vers MongoDB en documents enrichis (denormalized).

Strategie : chaque transaction MongoDB embarque tout son contexte (carte, client,
marchand, mcc, label fraude) pour servir efficacement les usages analytiques et ML.

Usage :
    python -m src.migration.load_mongo --limit 100000     # Echantillon
    python -m src.migration.load_mongo --limit 1000000    # 1 million
    python -m src.migration.load_mongo --all              # Tout (long)

Variables d'environnement requises (.env) :
    ORACLE_HOST, ORACLE_PORT, ORACLE_SERVICE_NAME, ORACLE_USER, ORACLE_PASSWORD
    MONGO_HOST, MONGO_PORT, MONGO_USER, MONGO_PASSWORD, MONGO_DATABASE
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Iterator

import oracledb
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import BulkWriteError
from tqdm import tqdm

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
load_dotenv()

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("load_mongo")

# Taille des batchs MongoDB (insert_many)
BATCH_SIZE = int(os.environ.get("MONGO_BATCH_SIZE", "10000"))
# Taille du curseur Oracle (lignes lues par appel reseau)
ORACLE_FETCH_SIZE = int(os.environ.get("ORACLE_FETCH_SIZE", "10000"))

COLLECTION_NAME = "transactions_enriched"


# -----------------------------------------------------------------------------
# Connexions
# -----------------------------------------------------------------------------
def get_oracle_connection() -> oracledb.Connection:
    """Connexion Oracle XE en mode thin."""
    dsn = oracledb.makedsn(
        host=os.environ["ORACLE_HOST"],
        port=int(os.environ["ORACLE_PORT"]),
        service_name=os.environ["ORACLE_SERVICE_NAME"],
    )
    conn = oracledb.connect(
        user=os.environ["ORACLE_USER"],
        password=os.environ["ORACLE_PASSWORD"],
        dsn=dsn,
    )
    logger.info("Connexion Oracle etablie")
    return conn


def get_mongo_client() -> MongoClient:
    """Connexion MongoDB."""
    user = os.environ.get("MONGO_USER", "admin")
    password = os.environ.get("MONGO_PASSWORD", "ChangeMeMongo2026")
    host = os.environ.get("MONGO_HOST", "localhost")
    port = int(os.environ.get("MONGO_PORT", "27017"))
    uri = f"mongodb://{user}:{password}@{host}:{port}/admin"
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    # Force la verification de connexion immediate
    client.admin.command("ping")
    logger.info("Connexion MongoDB etablie sur %s:%d", host, port)
    return client


# -----------------------------------------------------------------------------
# Construction du document enrichi
# -----------------------------------------------------------------------------
def build_enriched_query(limit: int | None = None) -> str:
    """Construit la requete Oracle qui assemble les documents.

    Optimisations vs version naive :
      - Pas d'ORDER BY : MongoDB s'en moque, et trier 13M lignes coute tres cher
      - Hint /*+ USE_HASH ... */ pour forcer un plan de jointure efficace
      - Hint /*+ FIRST_ROWS(N) */ pour commencer a streamer rapidement

    Note RGPD : on ne ramene PAS les colonnes chiffrees (yearly_income, address,
    PAN, CVV) dans Mongo, par respect du principe de minimisation des donnees.
    """
    hint = "/*+ USE_HASH(t c cl m mcc lf) FIRST_ROWS(1000) */"
    select = f"""
        SELECT {hint}
            t.id_transaction,
            t.date_transaction,
            t.amount,
            t.use_chip,
            t.situation_date,
            -- Carte
            c.id_carte,
            c.card_brand,
            c.card_type,
            c.has_chip,
            c.credit_limit,
            c.card_on_dark_web,
            -- Client (sans donnees sensibles chiffrees)
            cl.id_client,
            cl.current_age,
            cl.gender,
            cl.credit_score,
            cl.num_credit_cards,
            -- Marchand
            m.id_marchand,
            m.merchant_city,
            m.merchant_state,
            m.zip,
            -- MCC
            mcc.code_mcc,
            mcc.libelle_mcc,
            -- Label fraude (peut etre NULL)
            lf.is_fraud
        FROM       transaction t
        INNER JOIN carte        c   ON t.id_carte    = c.id_carte
        INNER JOIN client       cl  ON c.id_client   = cl.id_client
        INNER JOIN marchand     m   ON t.id_marchand = m.id_marchand
        INNER JOIN mcc              ON m.code_mcc    = mcc.code_mcc
        LEFT  JOIN label_fraude lf  ON t.id_transaction = lf.id_transaction
    """
    if limit:
        return f"SELECT * FROM ({select}) WHERE rownum <= {limit}"
    return select


def row_to_document(row: tuple, columns: list[str]) -> dict:
    """Transforme une ligne Oracle en document MongoDB enrichi.

    Strategie : embedding complet pour servir efficacement les usages analytiques.
    """
    r = dict(zip(columns, row))

    return {
        "id_transaction": int(r["ID_TRANSACTION"]),
        "date_transaction": r["DATE_TRANSACTION"],
        "amount": float(r["AMOUNT"]) if r["AMOUNT"] is not None else None,
        "use_chip": r["USE_CHIP"],
        "situation_date": r["SITUATION_DATE"],
        "carte": {
            "id_carte": int(r["ID_CARTE"]),
            "card_brand": r["CARD_BRAND"],
            "card_type": r["CARD_TYPE"],
            "has_chip": r["HAS_CHIP"] == "Y",
            "credit_limit": float(r["CREDIT_LIMIT"]) if r["CREDIT_LIMIT"] is not None else None,
            "card_on_dark_web": r["CARD_ON_DARK_WEB"] == "Y",
        },
        "client": {
            "id_client": int(r["ID_CLIENT"]),
            "current_age": int(r["CURRENT_AGE"]) if r["CURRENT_AGE"] is not None else None,
            "gender": r["GENDER"],
            "credit_score": int(r["CREDIT_SCORE"]) if r["CREDIT_SCORE"] is not None else None,
            "num_credit_cards": int(r["NUM_CREDIT_CARDS"]) if r["NUM_CREDIT_CARDS"] is not None else None,
        },
        "marchand": {
            "id_marchand": int(r["ID_MARCHAND"]),
            "ville": r["MERCHANT_CITY"],
            "etat": r["MERCHANT_STATE"],
            "zip": r["ZIP"],
        },
        "mcc": {
            "code": int(r["CODE_MCC"]),
            "libelle": r["LIBELLE_MCC"],
        },
        "fraude": {
            "is_fraud": r["IS_FRAUD"] == "Y" if r["IS_FRAUD"] is not None else None,
            "labelled": r["IS_FRAUD"] is not None,
        },
        "_ingested_at": datetime.now(timezone.utc),
    }


# -----------------------------------------------------------------------------
# Migration principale
# -----------------------------------------------------------------------------
def iter_oracle_rows(conn: oracledb.Connection, query: str) -> Iterator[tuple]:
    """Iterateur sur les lignes Oracle avec un curseur server-side optimise."""
    cursor = conn.cursor()
    cursor.arraysize = ORACLE_FETCH_SIZE
    cursor.prefetchrows = ORACLE_FETCH_SIZE + 1  # Reduit les aller-retours reseau
    cursor.execute(query)
    columns = [d[0] for d in cursor.description]
    while True:
        rows = cursor.fetchmany(ORACLE_FETCH_SIZE)
        if not rows:
            break
        for row in rows:
            yield row, columns
    cursor.close()


def migrate(limit: int | None, drop_existing: bool = False) -> int:
    """Lance la migration Oracle -> MongoDB.

    Args:
        limit: nombre max de transactions a migrer (None = tout)
        drop_existing: si True, supprime la collection existante avant migration

    Returns:
        Nombre de documents inseres.
    """
    oracle_conn = get_oracle_connection()
    mongo_client = get_mongo_client()

    try:
        db = mongo_client[os.environ.get("MONGO_DATABASE", "finsecure")]
        collection = db[COLLECTION_NAME]

        if drop_existing:
            logger.warning("Suppression de la collection existante %s", COLLECTION_NAME)
            collection.drop()

        # Estimation du total pour la progress bar
        if limit:
            total = limit
        else:
            count_cursor = oracle_conn.cursor()
            count_cursor.execute("SELECT COUNT(*) FROM transaction")
            total = count_cursor.fetchone()[0]
            count_cursor.close()

        logger.info("Demarrage de la migration : ~%d documents a inserer", total)
        logger.info("Strategie : documents enrichis (denormalized, embedding complet)")
        logger.info("Collection cible : %s.%s", db.name, COLLECTION_NAME)

        query = build_enriched_query(limit)

        batch: list[dict] = []
        total_inserted = 0

        with tqdm(total=total, desc="Mongo", unit="doc") as pbar:
            for row, columns in iter_oracle_rows(oracle_conn, query):
                doc = row_to_document(row, columns)
                batch.append(doc)
                if len(batch) >= BATCH_SIZE:
                    try:
                        collection.insert_many(batch, ordered=False)
                        total_inserted += len(batch)
                        pbar.update(len(batch))
                    except BulkWriteError as bwe:
                        logger.error("Erreur batch : %s", bwe.details.get("writeErrors", [])[:3])
                        raise
                    batch.clear()

            # Dernier batch
            if batch:
                collection.insert_many(batch, ordered=False)
                total_inserted += len(batch)
                pbar.update(len(batch))

        logger.info("Migration terminee : %d documents inseres", total_inserted)
        return total_inserted

    finally:
        oracle_conn.close()
        mongo_client.close()


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Migration Oracle -> MongoDB")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Nombre max de transactions a migrer (defaut: tout)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Equivalent a --limit=None : migre toutes les transactions",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Supprime la collection existante avant migration",
    )
    args = parser.parse_args()

    limit = None if args.all else args.limit

    try:
        n = migrate(limit=limit, drop_existing=args.drop)
        logger.info("OK %d documents", n)
        return 0
    except Exception as exc:  # noqa: BLE001
        logger.exception("Echec : %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
