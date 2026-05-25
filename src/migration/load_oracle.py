"""Migration des données sources (CSV + JSON + SQLite) vers Oracle XE.

Usage :
    python -m src.migration.load_oracle --step all
    python -m src.migration.load_oracle --step clients
    python -m src.migration.load_oracle --step cards
    python -m src.migration.load_oracle --step mcc
    python -m src.migration.load_oracle --step marchands
    python -m src.migration.load_oracle --step transactions
    python -m src.migration.load_oracle --step labels
    python -m src.migration.load_oracle --step errors

Dépendances :
    pip install oracledb pandas tqdm cryptography python-dotenv

Variables d'environnement requises (voir .env) :
    ORACLE_HOST, ORACLE_PORT, ORACLE_SERVICE_NAME, ORACLE_USER, ORACLE_PASSWORD
    ENCRYPTION_KEY
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

import oracledb
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

from src.migration.encryption import encrypt, encrypt_optional

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
load_dotenv()

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("load_oracle")

DATA_DIR = Path(os.environ.get("DATA_DIR", "data/raw"))
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "10000"))


# -----------------------------------------------------------------------------
# Connexion Oracle
# -----------------------------------------------------------------------------
def get_connection() -> oracledb.Connection:
    """Établit une connexion à Oracle XE en mode thin (sans Oracle Client)."""
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
    logger.info("Connexion Oracle établie sur %s", dsn)
    return conn


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def yn(value) -> str:
    """Convertit 'YES'/'NO' (CSV) vers 'Y'/'N' (CHAR(1) Oracle)."""
    if value is None or pd.isna(value):
        return "N"
    val = str(value).strip().upper()
    if val in ("YES", "Y", "TRUE", "1"):
        return "Y"
    return "N"


def s(value) -> Optional[str]:
    """Convertit en string Oracle-compatible, gere NaN/None.

    Pandas renvoie float('nan') pour les cellules vides. oracledb refuse
    d'inserer un float dans une colonne VARCHAR2. Cette fonction normalise.
    """
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    result = str(value).strip()
    return result if result else None


def i(value) -> Optional[int]:
    """Convertit en int ou None pour NaN/None."""
    if value is None or pd.isna(value):
        return None
    return int(value)


def f(value) -> Optional[float]:
    """Convertit en float ou None pour NaN/None."""
    if value is None or pd.isna(value):
        return None
    return float(value)


def batch_insert(
    conn: oracledb.Connection,
    sql: str,
    rows: Iterable[tuple],
    batch_size: int = BATCH_SIZE,
) -> int:
    """Insert massif par batch avec executemany. Retourne le nombre de lignes insérées."""
    cursor = conn.cursor()
    total = 0
    buffer: list = []
    for row in rows:
        buffer.append(row)
        if len(buffer) >= batch_size:
            cursor.executemany(sql, buffer)
            conn.commit()
            total += len(buffer)
            buffer = []
    if buffer:
        cursor.executemany(sql, buffer)
        conn.commit()
        total += len(buffer)
    cursor.close()
    return total


# -----------------------------------------------------------------------------
# Étapes de migration
# -----------------------------------------------------------------------------
def load_mcc(conn: oracledb.Connection) -> int:
    """Charge le référentiel MCC depuis mcc_codes.json."""
    logger.info("→ Chargement MCC")
    path = DATA_DIR / "mcc_codes.json"
    with open(path, encoding="utf-8") as f:
        mcc_data = json.load(f)

    sql = "INSERT INTO mcc (code_mcc, libelle_mcc) VALUES (:1, :2)"
    rows = ((int(code), libelle) for code, libelle in mcc_data.items())
    n = batch_insert(conn, sql, rows)
    logger.info("  %d codes MCC insérés", n)
    return n


def load_clients(conn: oracledb.Connection) -> int:
    """Charge les clients depuis users_data.csv avec chiffrement des colonnes KYC."""
    logger.info("→ Chargement CLIENT (avec chiffrement KYC)")
    path = DATA_DIR / "users_data.csv"
    df = pd.read_csv(path)

    sql = """
        INSERT INTO client (
            id_client, current_age, retirement_age, birth_year, birth_month,
            gender, address, latitude, longitude,
            per_capita_income, yearly_income, total_debt,
            credit_score, num_credit_cards
        ) VALUES (
            :1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12, :13, :14
        )
    """
    rows = []
    for _, r in tqdm(df.iterrows(), total=len(df), desc="Clients"):
        rows.append((
            int(r["id"]),
            int(r["current_age"]),
            i(r["retirement_age"]),
            int(r["birth_year"]),
            i(r["birth_month"]),
            s(r["gender"]),
            encrypt(s(r["address"])),
            f(r["latitude"]),
            f(r["longitude"]),
            encrypt_optional(s(r["per_capita_income"])),
            encrypt_optional(s(r["yearly_income"])),
            encrypt_optional(s(r["total_debt"])),
            i(r["credit_score"]),
            int(r["num_credit_cards"]),
        ))
    n = batch_insert(conn, sql, rows)
    logger.info("  %d clients insérés", n)
    return n


def load_cards(conn: oracledb.Connection) -> int:
    """Charge les cartes depuis cards_data.csv avec chiffrement PAN/CVV."""
    logger.info("→ Chargement CARTE (avec chiffrement PAN/CVV)")
    path = DATA_DIR / "cards_data.csv"
    df = pd.read_csv(path)

    sql = """
        INSERT INTO carte (
            id_carte, id_client, card_brand, card_type,
            card_number_enc, expires, cvv_enc, has_chip,
            num_cards_issued, credit_limit, acct_open_date,
            year_pin_last_changed, card_on_dark_web
        ) VALUES (
            :1, :2, :3, :4, :5, :6, :7, :8, :9, :10,
            TO_DATE(:11, 'YYYY-MM-DD'), :12, :13
        )
    """
    rows = []
    for _, r in tqdm(df.iterrows(), total=len(df), desc="Cartes"):
        # acct_open_date arrive parfois en MM/YYYY → on prend le 1er du mois
        open_date = r["acct_open_date"]
        if "/" in str(open_date):
            mm, yyyy = str(open_date).split("/")
            open_date = f"{yyyy}-{mm.zfill(2)}-01"
        # credit_limit arrive en "$XXX" → on enlève le $
        credit_lim = str(r["credit_limit"]).replace("$", "").replace(",", "")
        credit_lim = float(credit_lim) if credit_lim else None

        rows.append((
            int(r["id"]),
            int(r["client_id"]),
            s(r["card_brand"]),
            s(r["card_type"]),
            encrypt(str(r["card_number"])),
            s(r["expires"]),
            encrypt(str(r["cvv"])),
            yn(r.get("has_chip")),
            i(r["num_cards_issued"]),
            credit_lim,
            open_date,
            i(r["year_pin_last_changed"]),
            yn(r.get("card_on_dark_web")),
        ))
    n = batch_insert(conn, sql, rows)
    logger.info("  %d cartes insérées", n)
    return n


def load_marchands(conn: oracledb.Connection) -> int:
    """Charge la dimension MARCHAND par DISTINCT depuis transactions_data.csv.

    On lit le CSV en chunks et on accumule les marchands distincts pour ne
    pas dépasser la mémoire sur 22 M lignes.
    """
    logger.info("→ Chargement MARCHAND (déduplication depuis transactions)")
    path = DATA_DIR / "transactions_data.csv"
    seen: dict[int, dict] = {}
    chunk_size = 500_000

    for chunk in tqdm(
        pd.read_csv(path, chunksize=chunk_size, usecols=["merchant_id", "mcc", "merchant_city", "merchant_state", "zip"]),
        desc="Lecture chunks",
    ):
        for _, r in chunk.iterrows():
            mid = int(r["merchant_id"])
            if mid not in seen:
                seen[mid] = {
                    "code_mcc": int(r["mcc"]),
                    "merchant_city": s(r["merchant_city"]),
                    "merchant_state": s(r["merchant_state"]),
                    "zip": s(r["zip"]),
                }

    sql = """
        INSERT INTO marchand (id_marchand, code_mcc, merchant_city, merchant_state, zip)
        VALUES (:1, :2, :3, :4, :5)
    """
    rows = (
        (mid, v["code_mcc"], v["merchant_city"], v["merchant_state"], v["zip"])
        for mid, v in seen.items()
    )
    n = batch_insert(conn, sql, rows)
    logger.info("  %d marchands insérés (déduit de %d transactions lues)", n, sum(1 for _ in seen))
    return n


def load_transactions(conn: oracledb.Connection, situation_date: str | None = None) -> int:
    """Charge les transactions depuis transactions_data.csv par chunks."""
    logger.info("→ Chargement TRANSACTION (par chunks)")
    situation_date = situation_date or datetime.now().strftime("%Y-%m-%d")
    path = DATA_DIR / "transactions_data.csv"
    chunk_size = 100_000

    sql = """
        INSERT INTO transaction (
            id_transaction, id_carte, id_marchand,
            date_transaction, amount, use_chip, situation_date
        ) VALUES (
            :1, :2, :3,
            TO_TIMESTAMP(:4, 'YYYY-MM-DD HH24:MI:SS'),
            :5, :6, TO_DATE(:7, 'YYYY-MM-DD')
        )
    """
    total = 0
    for chunk in tqdm(pd.read_csv(path, chunksize=chunk_size), desc="Transactions"):
        rows = []
        for _, r in chunk.iterrows():
            # amount arrive en "$XX.XX"
            amt = str(r["amount"]).replace("$", "").replace(",", "")
            amt = float(amt) if amt else 0.0
            # date arrive en "YYYY-MM-DD HH:MM:SS" déjà
            rows.append((
                int(r["id"]),
                int(r["card_id"]),
                int(r["merchant_id"]),
                str(r["date"]),
                amt,
                s(r["use_chip"]),
                situation_date,
            ))
        total += batch_insert(conn, sql, rows)
    logger.info("  %d transactions insérées", total)
    return total


def load_labels(conn: oracledb.Connection) -> int:
    """Charge les labels de fraude depuis train_fraud_labels.json."""
    logger.info("→ Chargement LABEL_FRAUDE")
    path = DATA_DIR / "train_fraud_labels.json"
    with open(path, encoding="utf-8") as f:
        labels = json.load(f)
    # Format attendu : { "target": { "id_transaction": "Yes"/"No", ... } }
    label_dict = labels.get("target", labels)

    sql = "INSERT INTO label_fraude (id_transaction, is_fraud) VALUES (:1, :2)"
    rows = (
        (int(tx_id), yn(label))
        for tx_id, label in label_dict.items()
    )
    n = batch_insert(conn, sql, rows)
    logger.info("  %d labels insérés", n)
    return n


def load_errors(conn: oracledb.Connection) -> int:
    """Charge les erreurs en éclatant la colonne multi-valuée errors."""
    logger.info("→ Chargement ERREUR_TRANSACTION (éclatement)")
    path = DATA_DIR / "transactions_data.csv"
    chunk_size = 100_000

    sql = """
        INSERT INTO erreur_transaction (id_erreur, id_transaction, code_erreur)
        VALUES (seq_erreur_transaction.NEXTVAL, :1, :2)
    """
    total = 0
    for chunk in tqdm(
        pd.read_csv(path, chunksize=chunk_size, usecols=["id", "errors"]),
        desc="Erreurs",
    ):
        rows = []
        for _, r in chunk.iterrows():
            errors = r.get("errors")
            if pd.isna(errors) or not errors:
                continue
            for code in str(errors).split(","):
                code = code.strip()
                if code:
                    rows.append((int(r["id"]), code))
        if rows:
            total += batch_insert(conn, sql, rows)
    logger.info("  %d erreurs insérées", total)
    return total


# -----------------------------------------------------------------------------
# Orchestration
# -----------------------------------------------------------------------------
STEPS = {
    "mcc": load_mcc,
    "clients": load_clients,
    "cards": load_cards,
    "marchands": load_marchands,
    "transactions": load_transactions,
    "labels": load_labels,
    "errors": load_errors,
}

ORDER = ["mcc", "clients", "cards", "marchands", "transactions", "labels", "errors"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Migration des données vers Oracle XE")
    parser.add_argument(
        "--step",
        choices=["all", *ORDER],
        default="all",
        help="Étape à exécuter",
    )
    args = parser.parse_args()

    conn = get_connection()
    try:
        steps_to_run = ORDER if args.step == "all" else [args.step]
        for step in steps_to_run:
            STEPS[step](conn)
        logger.info("✓ Migration terminée")
        return 0
    except Exception as exc:  # noqa: BLE001
        logger.exception("✗ Échec de la migration : %s", exc)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
