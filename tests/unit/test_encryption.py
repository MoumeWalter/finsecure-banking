"""Tests unitaires du module de chiffrement AES-256-GCM."""

from __future__ import annotations

import base64
import secrets

import pytest

from src.migration.encryption import (
    _get_key_from_env,
    decrypt,
    encrypt,
    encrypt_optional,
)

pytestmark = pytest.mark.unit


# Cle de test fixe (32 bytes) - ne jamais utiliser en production !
TEST_KEY = secrets.token_bytes(32)


class TestEncryptDecrypt:
    """Cycles aller-retour encrypt / decrypt."""

    def test_aller_retour_simple(self):
        """Une chaine simple doit etre identique apres encrypt + decrypt."""
        plaintext = "Walter Moume"
        ciphertext = encrypt(plaintext, key=TEST_KEY)
        assert ciphertext is not None
        assert ciphertext != plaintext  # le ciphertext doit etre different
        assert decrypt(ciphertext, key=TEST_KEY) == plaintext

    def test_aller_retour_caracteres_speciaux(self):
        """Doit gerer les caracteres UTF-8 (accents, emojis)."""
        plaintext = "Élise — café à 5€ 🏦"
        ciphertext = encrypt(plaintext, key=TEST_KEY)
        assert decrypt(ciphertext, key=TEST_KEY) == plaintext

    def test_aller_retour_long(self):
        """Doit gerer les chaines longues (jusqu'a la taille max d'une colonne)."""
        plaintext = "A" * 1000
        ciphertext = encrypt(plaintext, key=TEST_KEY)
        assert decrypt(ciphertext, key=TEST_KEY) == plaintext

    def test_aller_retour_numerique_via_helper(self):
        """encrypt_optional doit convertir les valeurs en str."""
        ciphertext = encrypt_optional(75000.50, key=TEST_KEY)
        assert decrypt(ciphertext, key=TEST_KEY) == "75000.5"


class TestNullHandling:
    """Gestion des valeurs nulles (None, chaine vide)."""

    def test_encrypt_none(self):
        assert encrypt(None, key=TEST_KEY) is None

    def test_encrypt_empty_string(self):
        assert encrypt("", key=TEST_KEY) is None

    def test_decrypt_none(self):
        assert decrypt(None, key=TEST_KEY) is None

    def test_decrypt_empty_string(self):
        assert decrypt("", key=TEST_KEY) is None

    def test_encrypt_optional_none(self):
        assert encrypt_optional(None, key=TEST_KEY) is None


class TestSecurity:
    """Proprietes de securite du chiffrement."""

    def test_meme_plaintext_ciphertexts_differents(self):
        """Le meme plaintext chiffre deux fois doit donner deux ciphertexts
        differents (grace au nonce aleatoire de 12 bytes)."""
        plaintext = "12 rue de la Republique 75001 Paris"
        c1 = encrypt(plaintext, key=TEST_KEY)
        c2 = encrypt(plaintext, key=TEST_KEY)
        assert c1 != c2  # nonces differents
        # Mais les deux dechiffrent vers le meme plaintext
        assert decrypt(c1, key=TEST_KEY) == decrypt(c2, key=TEST_KEY) == plaintext

    def test_decrypt_avec_mauvaise_cle_leve_erreur(self):
        """Dechiffrer avec une autre cle doit echouer (proprietete GCM)."""
        plaintext = "secret"
        ciphertext = encrypt(plaintext, key=TEST_KEY)
        wrong_key = secrets.token_bytes(32)
        with pytest.raises(Exception):  # InvalidTag de la lib cryptography
            decrypt(ciphertext, key=wrong_key)

    def test_ciphertext_est_base64_valide(self):
        """Le ciphertext doit etre base64 decodable."""
        ciphertext = encrypt("test", key=TEST_KEY)
        # Doit etre decodable sans exception
        raw = base64.b64decode(ciphertext)
        # 12 bytes de nonce + tag (16) + ciphertext (au moins 4 bytes pour "test")
        assert len(raw) >= 12 + 16


class TestEnvKey:
    """Lecture de la cle depuis l'environnement."""

    def test_env_key_absente_leve_erreur(self, monkeypatch):
        monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
        with pytest.raises(ValueError, match="ENCRYPTION_KEY"):
            _get_key_from_env()

    def test_env_key_mauvaise_taille_leve_erreur(self, monkeypatch):
        """Une cle de 16 bytes (AES-128) doit etre refusee, on veut AES-256."""
        too_short = base64.b64encode(secrets.token_bytes(16)).decode()
        monkeypatch.setenv("ENCRYPTION_KEY", too_short)
        with pytest.raises(ValueError, match="32 bytes"):
            _get_key_from_env()

    def test_env_key_valide(self, monkeypatch):
        valid_key = base64.b64encode(secrets.token_bytes(32)).decode()
        monkeypatch.setenv("ENCRYPTION_KEY", valid_key)
        result = _get_key_from_env()
        assert len(result) == 32

    def test_env_key_base64_invalide_leve_erreur(self, monkeypatch):
        monkeypatch.setenv("ENCRYPTION_KEY", "ceci n'est pas du base64 !!!")
        with pytest.raises(ValueError, match="base64"):
            _get_key_from_env()
