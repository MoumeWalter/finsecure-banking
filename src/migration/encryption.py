"""Chiffrement AES-256-GCM des colonnes sensibles avant insertion en base.

Ce module fournit deux fonctions principales :
    - encrypt(plaintext, key) : chiffre une chaîne et retourne le ciphertext base64
    - decrypt(ciphertext, key) : opération inverse

La clé est chargée depuis la variable d'environnement ENCRYPTION_KEY (32 bytes
en base64). Le format de sortie inclut le nonce (12 bytes) pour permettre le
déchiffrement.

Conformité : RGPD article 32 (sécurité des données personnelles), PCI-DSS sur
les colonnes card_number_enc et cvv_enc.
"""

from __future__ import annotations

import base64
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _get_key_from_env() -> bytes:
    """Récupère la clé de chiffrement depuis l'environnement.

    Returns:
        bytes: clé AES-256 (32 bytes)

    Raises:
        ValueError: si ENCRYPTION_KEY n'est pas définie ou mal formée.
    """
    key_b64 = os.environ.get("ENCRYPTION_KEY")
    if not key_b64:
        raise ValueError(
            "ENCRYPTION_KEY n'est pas définie. "
            "Générer une clé avec : python -c 'import secrets, base64; "
            "print(base64.b64encode(secrets.token_bytes(32)).decode())'"
        )
    try:
        key = base64.b64decode(key_b64)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"ENCRYPTION_KEY invalide (base64 attendu) : {exc}") from exc
    if len(key) != 32:
        raise ValueError(f"ENCRYPTION_KEY doit faire 32 bytes, reçu {len(key)}")
    return key


def encrypt(plaintext: Optional[str], key: Optional[bytes] = None) -> Optional[str]:
    """Chiffre une chaîne avec AES-256-GCM.

    Args:
        plaintext: la chaîne à chiffrer (None retourne None).
        key: clé optionnelle. Si non fournie, lue depuis l'environnement.

    Returns:
        str: ciphertext base64 (incluant le nonce de 12 bytes en préfixe),
             ou None si plaintext était None.
    """
    if plaintext is None or plaintext == "":
        return None
    if key is None:
        key = _get_key_from_env()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    # Format final : base64(nonce || ciphertext)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def decrypt(ciphertext_b64: Optional[str], key: Optional[bytes] = None) -> Optional[str]:
    """Déchiffre une chaîne produite par encrypt().

    Args:
        ciphertext_b64: chaîne base64 produite par encrypt().
        key: clé optionnelle. Si non fournie, lue depuis l'environnement.

    Returns:
        str: plaintext original, ou None si l'entrée était None.
    """
    if ciphertext_b64 is None or ciphertext_b64 == "":
        return None
    if key is None:
        key = _get_key_from_env()
    raw = base64.b64decode(ciphertext_b64)
    nonce, ciphertext = raw[:12], raw[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


def encrypt_optional(value, key: Optional[bytes] = None) -> Optional[str]:
    """Helper : chiffre une valeur en convertissant d'abord en str.

    Utile pour les colonnes numériques (yearly_income, total_debt…) qu'on
    veut stocker chiffrées sous forme de texte.
    """
    if value is None:
        return None
    return encrypt(str(value), key)


if __name__ == "__main__":
    # Démo rapide en ligne de commande
    import argparse

    parser = argparse.ArgumentParser(description="Chiffrement/déchiffrement AES-256-GCM")
    parser.add_argument("action", choices=["encrypt", "decrypt", "gen_key"])
    parser.add_argument("--value", help="Valeur à chiffrer/déchiffrer")
    args = parser.parse_args()

    if args.action == "gen_key":
        import secrets

        key = secrets.token_bytes(32)
        print(base64.b64encode(key).decode())
    elif args.action == "encrypt":
        print(encrypt(args.value))
    elif args.action == "decrypt":
        print(decrypt(args.value))
