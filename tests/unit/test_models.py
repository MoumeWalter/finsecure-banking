"""Tests unitaires des schemas Pydantic de l'API."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.api.models import (
    CarteEmbedded,
    ClientEmbedded,
    FraudeEmbedded,
    FraudStats,
    HealthCheck,
    MarchandEmbedded,
    McEmbedded,
    TransactionEnriched,
)

pytestmark = pytest.mark.unit


class TestEmbeddedModels:
    """Schemas embarques dans une transaction."""

    def test_carte_embedded_complete(self):
        carte = CarteEmbedded(
            id_carte=4938,
            card_brand="Visa",
            card_type="Credit",
            has_chip=True,
            credit_limit=5000.0,
            card_on_dark_web=False,
        )
        assert carte.id_carte == 4938
        assert carte.has_chip is True

    def test_carte_embedded_champs_optionnels(self):
        """Tous les champs sauf id_carte sont optionnels."""
        carte = CarteEmbedded(id_carte=1)
        assert carte.id_carte == 1
        assert carte.card_brand is None

    def test_client_embedded(self):
        client = ClientEmbedded(
            id_client=1066,
            current_age=59,
            gender="Female",
            credit_score=720,
            num_credit_cards=3,
        )
        assert client.id_client == 1066
        assert client.credit_score == 720

    def test_marchand_embedded(self):
        marchand = MarchandEmbedded(id_marchand=2503, ville="Paris", etat="Ile-de-France")
        assert marchand.ville == "Paris"

    def test_mcc_embedded(self):
        mcc = McEmbedded(code=5814, libelle="Fast Food Restaurants")
        assert mcc.code == 5814

    def test_fraude_embedded_labellisee(self):
        fraude = FraudeEmbedded(is_fraud=True, labelled=True)
        assert fraude.is_fraud is True
        assert fraude.labelled is True

    def test_fraude_embedded_non_labellisee(self):
        """Si labelled=False, is_fraud peut etre None."""
        fraude = FraudeEmbedded(is_fraud=None, labelled=False)
        assert fraude.is_fraud is None


class TestTransactionEnriched:
    """Schema principal de l'API."""

    def test_transaction_minimale(self):
        """Une transaction valide avec champs minimum."""
        tx = TransactionEnriched(
            id_transaction=1,
            carte=CarteEmbedded(id_carte=1),
            client=ClientEmbedded(id_client=1),
            marchand=MarchandEmbedded(id_marchand=1),
            mcc=McEmbedded(code=1234),
            fraude=FraudeEmbedded(),
        )
        assert tx.id_transaction == 1

    def test_transaction_manque_champ_requis(self):
        """Sans `carte`, la validation echoue."""
        with pytest.raises(ValidationError):
            TransactionEnriched(
                id_transaction=1,
                client=ClientEmbedded(id_client=1),
                marchand=MarchandEmbedded(id_marchand=1),
                mcc=McEmbedded(code=1234),
                fraude=FraudeEmbedded(),
            )  # type: ignore[call-arg]

    def test_transaction_depuis_dict_mongo(self):
        """Reconstruction depuis un dict tel que renvoye par MongoDB."""
        doc = {
            "id_transaction": 7475327,
            "date_transaction": None,
            "amount": -77.0,
            "use_chip": "Swipe Transaction",
            "situation_date": None,
            "carte": {
                "id_carte": 5497,
                "card_brand": "Mastercard",
                "card_type": "Debit",
                "has_chip": True,
                "credit_limit": 13555,
                "card_on_dark_web": False,
            },
            "client": {
                "id_client": 126,
                "current_age": 63,
                "gender": "Male",
                "credit_score": 799,
                "num_credit_cards": 4,
            },
            "marchand": {"id_marchand": 90999, "ville": "ONLINE", "etat": None, "zip": None},
            "mcc": {"code": 4722, "libelle": "Travel Agencies"},
            "fraude": {"is_fraud": True, "labelled": True},
        }
        tx = TransactionEnriched(**doc)
        assert tx.id_transaction == 7475327
        assert tx.carte.card_brand == "Mastercard"
        assert tx.fraude.is_fraud is True


class TestUtilityModels:
    """Schemas utilitaires."""

    def test_healthcheck(self):
        hc = HealthCheck(
            status="ok",
            api_version="0.1.0",
            mongodb={"connected": True, "estimated_documents": 100000},
        )
        assert hc.status == "ok"
        assert hc.mongodb["estimated_documents"] == 100000

    def test_fraud_stats(self):
        stats = FraudStats(
            total_transactions=100000,
            nb_fraudes=107,
            taux_global_pct=0.107,
            par_genre={"Female": 77, "Male": 30},
            par_type_paiement={"Online Transaction": 98, "Swipe Transaction": 9},
        )
        assert stats.nb_fraudes == 107
        assert stats.par_genre["Female"] == 77
        # Verification metier : la somme par genre = total fraudes
        assert sum(stats.par_genre.values()) == stats.nb_fraudes
