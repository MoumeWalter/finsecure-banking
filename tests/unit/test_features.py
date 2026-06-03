"""Tests unitaires du feature engineering ML."""

from __future__ import annotations

import pytest

from src.ml.features import (
    CATEGORICAL_FEATURES,
    DEFAULT_AGE,
    DEFAULT_HOUR,
    DEFAULT_USE_CHIP,
    FEATURE_COLUMNS,
    NUMERICAL_FEATURES,
    extract_features_from_mongo_doc,
    extract_label,
    features_from_request,
    to_dataframe,
)

pytestmark = pytest.mark.unit


# -----------------------------------------------------------------------------
# extract_features_from_mongo_doc
# -----------------------------------------------------------------------------
class TestExtractFeaturesFromMongoDoc:
    def test_doc_complet(self):
        doc = {
            "amount": 123.45,
            "use_chip": "Online Transaction",
            "date": "2024-01-15T14:30:00",
            "client": {"current_age": 35, "gender": "Female"},
            "marchand": {"state": "CA"},
            "mcc": {"code": 5411},
        }
        result = extract_features_from_mongo_doc(doc)
        assert result["amount"] == 123.45
        assert result["use_chip"] == "Online Transaction"
        assert result["mcc_code"] == 5411
        assert result["merchant_state"] == "CA"
        assert result["hour"] == 14
        assert result["current_age"] == 35.0
        assert result["gender"] == "Female"

    def test_doc_partiel_applique_defaults(self):
        """Un doc avec champs manquants doit recevoir les defaults."""
        doc = {"amount": 50.0}
        result = extract_features_from_mongo_doc(doc)
        assert result["amount"] == 50.0
        assert result["use_chip"] == DEFAULT_USE_CHIP
        assert result["mcc_code"] == 0
        assert result["hour"] == DEFAULT_HOUR
        assert result["current_age"] == DEFAULT_AGE

    def test_amount_null_devient_zero(self):
        doc = {"amount": None}
        result = extract_features_from_mongo_doc(doc)
        assert result["amount"] == 0.0

    def test_date_invalide_utilise_default(self):
        doc = {"amount": 10.0, "date": "pas-une-date"}
        result = extract_features_from_mongo_doc(doc)
        assert result["hour"] == DEFAULT_HOUR


# -----------------------------------------------------------------------------
# extract_label
# -----------------------------------------------------------------------------
class TestExtractLabel:
    def test_fraude_labellisee_yes(self):
        doc = {"fraude": {"is_labellisee": True, "is_fraud": "Yes"}}
        assert extract_label(doc) == 1

    def test_fraude_labellisee_no(self):
        doc = {"fraude": {"is_labellisee": True, "is_fraud": "No"}}
        assert extract_label(doc) == 0

    def test_non_labellisee_retourne_none(self):
        doc = {"fraude": {"is_labellisee": False}}
        assert extract_label(doc) is None

    def test_fraude_absente_retourne_none(self):
        doc = {}
        assert extract_label(doc) is None


# -----------------------------------------------------------------------------
# features_from_request
# -----------------------------------------------------------------------------
class TestFeaturesFromRequest:
    def test_requete_complete(self):
        request = {
            "amount": 200.0,
            "use_chip": "Chip Transaction",
            "mcc_code": 4900,
            "merchant_state": "TX",
            "hour": 9,
            "current_age": 28.5,
            "gender": "Male",
        }
        result = features_from_request(request)
        assert result["amount"] == 200.0
        assert result["mcc_code"] == 4900
        assert result["hour"] == 9
        assert result["gender"] == "Male"

    def test_requete_minimale_applique_defaults(self):
        request = {"amount": 50.0}
        result = features_from_request(request)
        assert result["amount"] == 50.0
        assert result["hour"] == DEFAULT_HOUR
        assert result["current_age"] == DEFAULT_AGE
        assert result["use_chip"] == DEFAULT_USE_CHIP

    def test_hour_zero_pas_remplace_par_default(self):
        """hour=0 est valide et ne doit pas etre remplace par DEFAULT_HOUR."""
        request = {"amount": 50.0, "hour": 0}
        result = features_from_request(request)
        assert result["hour"] == 0


# -----------------------------------------------------------------------------
# to_dataframe
# -----------------------------------------------------------------------------
class TestToDataframe:
    def test_dict_unique(self):
        features = {col: 1 for col in FEATURE_COLUMNS}
        df = to_dataframe(features)
        assert len(df) == 1
        assert list(df.columns) == FEATURE_COLUMNS

    def test_liste_de_dicts(self):
        features = [{col: i for col in FEATURE_COLUMNS} for i in range(3)]
        df = to_dataframe(features)
        assert len(df) == 3

    def test_ordre_des_colonnes(self):
        # Meme si on passe les features dans un ordre different,
        # le DataFrame doit avoir les colonnes dans FEATURE_COLUMNS
        features = {col: 1 for col in reversed(FEATURE_COLUMNS)}
        df = to_dataframe(features)
        assert list(df.columns) == FEATURE_COLUMNS


# -----------------------------------------------------------------------------
# Constantes
# -----------------------------------------------------------------------------
class TestConstants:
    def test_feature_columns_coherentes(self):
        """Verifie que NUMERICAL + CATEGORICAL = FEATURE_COLUMNS."""
        assert set(NUMERICAL_FEATURES + CATEGORICAL_FEATURES) == set(FEATURE_COLUMNS)
        assert len(NUMERICAL_FEATURES) + len(CATEGORICAL_FEATURES) == len(FEATURE_COLUMNS)
