"""Tests unitaires de la configuration (Pydantic Settings)."""

from __future__ import annotations

import pytest

from src.api.config import Settings, get_settings

pytestmark = pytest.mark.unit


class TestSettings:
    """Construction et validation de la configuration."""

    def test_defaults(self):
        """Les valeurs par defaut sont sensees."""
        settings = Settings(_env_file=None)
        assert settings.app_name == "FinSecure Banking API"
        assert settings.app_version == "0.1.0"
        assert settings.mongo_port == 27017
        assert settings.default_page_size > 0
        assert settings.max_page_size >= settings.default_page_size

    def test_mongo_uri_construit_correctement(self):
        """L'URI MongoDB doit etre formattee avec les bons composants."""
        settings = Settings(
            _env_file=None,
            mongo_host="myhost",
            mongo_port=12345,
            mongo_user="testuser",
            mongo_password="testpass",
        )
        uri = settings.mongo_uri
        assert uri.startswith("mongodb://")
        assert "testuser" in uri
        assert "testpass" in uri
        assert "myhost:12345" in uri
        assert uri.endswith("/admin")

    def test_page_size_validation(self):
        """page_size doit etre dans les bornes."""
        with pytest.raises(Exception):  # ValidationError de pydantic
            Settings(_env_file=None, default_page_size=0)
        with pytest.raises(Exception):
            Settings(_env_file=None, default_page_size=999_999)

    def test_settings_lit_l_environnement(self, monkeypatch):
        """Les variables d'env surchargent les defauts."""
        monkeypatch.setenv("MONGO_HOST", "override.example.com")
        monkeypatch.setenv("MONGO_PORT", "9999")
        s = Settings(_env_file=None)
        assert s.mongo_host == "override.example.com"
        assert s.mongo_port == 9999


class TestGetSettingsCache:
    """get_settings() est decoree avec @lru_cache."""

    def test_singleton(self):
        """Deux appels successifs retournent la meme instance."""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
