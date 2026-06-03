"""Entrainement du modele de detection de fraude.

Lit les transactions enrichies depuis MongoDB, construit les features,
entraine un RandomForestClassifier avec class_weight='balanced' pour
gerer le desequilibre (fraudes ~0.1%), evalue sur un split stratifie,
et sauvegarde le modele + metadonnees dans models/.

Usage :
    python -m src.ml.train

Variables d'environnement :
    MONGO_URI       : URI MongoDB (default: mongodb://admin:ChangeMeMongo2026@localhost:27017)
    MONGO_DB        : nom de la base (default: finsecure)
    MONGO_COLLECTION: nom de la collection (default: transactions_enriched)
    MODEL_OUTPUT_DIR: dossier de sortie (default: models)
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from pymongo import MongoClient
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder, StandardScaler

from src.ml.features import (
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    NUMERICAL_FEATURES,
    extract_features_from_mongo_doc,
    extract_label,
)

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

MODEL_VERSION = "1.0.0"
MODEL_TYPE = "RandomForestClassifier"
RANDOM_STATE = 42
TEST_SIZE = 0.2


# -----------------------------------------------------------------------------
# Chargement des donnees depuis MongoDB
# -----------------------------------------------------------------------------
def load_data_from_mongo(uri: str, db_name: str, collection_name: str) -> pd.DataFrame:
    """Charge les transactions labellisees depuis MongoDB et extrait les features."""
    logger.info("Connexion a MongoDB : %s/%s", db_name, collection_name)
    client = MongoClient(uri)
    collection = client[db_name][collection_name]

    # Verifier que la collection existe et contient des donnees
    total_in_collection = collection.estimated_document_count()
    logger.info("Documents dans la collection : %s", total_in_collection)

    if total_in_collection == 0:
        logger.error("Collection vide. Verifier le nom de la collection.")
        client.close()
        return pd.DataFrame()

    # Filtre : on prend les transactions labellisees (peu importe is_fraud)
    # On supporte les 2 conventions de naming (labelled / is_labellisee)
    query = {
        "$or": [
            {"fraude.labelled": True},
            {"fraude.is_labellisee": True},
        ]
    }

    cursor = collection.find(
        query,
        projection={
            "_id": 0,
            "amount": 1,
            "use_chip": 1,
            "date": 1,
            "date_transaction": 1,
            "client.current_age": 1,
            "client.gender": 1,
            "marchand.state": 1,
            "marchand.etat": 1,
            "mcc.code": 1,
            "fraude.labelled": 1,
            "fraude.is_labellisee": 1,
            "fraude.is_fraud": 1,
        },
    )

    features_list = []
    labels_list = []
    n_total = 0
    n_skipped = 0

    for doc in cursor:
        n_total += 1
        label = extract_label(doc)
        if label is None:
            n_skipped += 1
            continue
        features_list.append(extract_features_from_mongo_doc(doc))
        labels_list.append(label)

        # Log progress every 50k docs
        if n_total % 50000 == 0:
            logger.info("  Charge : %s docs (kept : %s)", n_total, len(features_list))

    client.close()

    logger.info("Documents traites : %s (skipped non labellises : %s)", n_total, n_skipped)

    if not features_list:
        logger.error("Aucune transaction labellisee trouvee.")
        return pd.DataFrame()

    df = pd.DataFrame(features_list)
    df["label"] = labels_list

    n_fraud = df["label"].sum()
    n_total_clean = len(df)
    logger.info(
        "Distribution : %s fraudes / %s total (%.4f%%)",
        n_fraud,
        n_total_clean,
        100 * n_fraud / max(n_total_clean, 1),
    )

    return df


# -----------------------------------------------------------------------------
# Construction du pipeline scikit-learn
# -----------------------------------------------------------------------------
def build_pipeline() -> Pipeline:
    """Construit le pipeline preprocessing + modele."""
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERICAL_FEATURES),
            (
                "cat",
                OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1),
                CATEGORICAL_FEATURES,
            ),
        ]
    )

    classifier = RandomForestClassifier(
        n_estimators=100,
        max_depth=12,
        min_samples_split=10,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    return Pipeline(steps=[("preprocessor", preprocessor), ("classifier", classifier)])


# -----------------------------------------------------------------------------
# Evaluation du modele
# -----------------------------------------------------------------------------
def evaluate(pipeline: Pipeline, X_test: pd.DataFrame, y_test: pd.Series) -> dict[str, Any]:
    """Calcule les metriques sur le set de test."""
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]

    metrics = {
        "roc_auc": float(roc_auc_score(y_test, y_proba)),
        "precision_fraud": float(precision_score(y_test, y_pred, pos_label=1, zero_division=0)),
        "recall_fraud": float(recall_score(y_test, y_pred, pos_label=1, zero_division=0)),
        "f1_fraud": float(f1_score(y_test, y_pred, pos_label=1, zero_division=0)),
        "n_test": int(len(y_test)),
        "n_fraud_test": int(y_test.sum()),
    }

    cm = confusion_matrix(y_test, y_pred)
    if cm.shape == (2, 2):
        metrics["confusion_matrix"] = {
            "true_negative": int(cm[0, 0]),
            "false_positive": int(cm[0, 1]),
            "false_negative": int(cm[1, 0]),
            "true_positive": int(cm[1, 1]),
        }

    logger.info("=" * 60)
    logger.info("RESULTATS DU MODELE")
    logger.info("=" * 60)
    logger.info("  ROC-AUC        : %.4f", metrics["roc_auc"])
    logger.info("  Precision      : %.4f", metrics["precision_fraud"])
    logger.info("  Recall         : %.4f", metrics["recall_fraud"])
    logger.info("  F1 score       : %.4f", metrics["f1_fraud"])
    logger.info("=" * 60)
    logger.info("Classification report :\n%s", classification_report(y_test, y_pred))

    return metrics


# -----------------------------------------------------------------------------
# Sauvegarde du modele + metadonnees
# -----------------------------------------------------------------------------
def save_model(pipeline: Pipeline, metrics: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    """Sauvegarde le pipeline et les metadonnees JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)

    model_path = output_dir / "fraud_detector.pkl"
    metadata_path = output_dir / "model_metadata.json"

    joblib.dump(pipeline, model_path)
    logger.info("Modele sauvegarde : %s (%.2f Mo)", model_path, model_path.stat().st_size / 1024 / 1024)

    metadata = {
        "model_version": MODEL_VERSION,
        "model_type": MODEL_TYPE,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "feature_columns": FEATURE_COLUMNS,
        "numerical_features": NUMERICAL_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "metrics": metrics,
        "hyperparameters": {
            "n_estimators": 100,
            "max_depth": 12,
            "min_samples_split": 10,
            "min_samples_leaf": 5,
            "class_weight": "balanced",
            "random_state": RANDOM_STATE,
        },
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Metadonnees sauvegardees : %s", metadata_path)

    return model_path, metadata_path


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main() -> int:
    mongo_uri = os.environ.get(
        "MONGO_URI", "mongodb://admin:ChangeMeMongo2026@localhost:27017"
    )
    mongo_db = os.environ.get("MONGO_DB", "finsecure")
    # NOTE: la collection s'appelle "transactions_enriched" (pas "enriched_transactions")
    mongo_collection = os.environ.get("MONGO_COLLECTION", "transactions_enriched")
    output_dir = Path(os.environ.get("MODEL_OUTPUT_DIR", "models"))

    logger.info("=== Entrainement du modele de detection de fraude ===")
    logger.info("Version : %s | Type : %s", MODEL_VERSION, MODEL_TYPE)

    # 1. Chargement
    df = load_data_from_mongo(mongo_uri, mongo_db, mongo_collection)
    if len(df) < 100:
        logger.error("Pas assez de donnees pour entrainer (%s lignes). Au moins 100 requises.", len(df))
        return 1

    # 2. Split
    X = df[FEATURE_COLUMNS]
    y = df["label"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE
    )
    logger.info("Split : %s train, %s test (stratified)", len(X_train), len(X_test))

    # 3. Construction et entrainement
    logger.info("Construction du pipeline et entrainement (peut prendre 1-2 min)...")
    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)
    logger.info("Entrainement termine.")

    # 4. Evaluation
    metrics = evaluate(pipeline, X_test, y_test)

    # 5. Sauvegarde
    model_path, metadata_path = save_model(pipeline, metrics, output_dir)

    logger.info("=== Entrainement complete avec succes ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
