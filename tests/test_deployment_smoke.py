"""Static deployment and production-configuration smoke tests."""

from pathlib import Path

import pytest
import yaml

from app import create_app
from app.config import DevelopmentConfig, ProductionConfig, TestingConfig

ROOT = Path(__file__).resolve().parents[1]


def test_configuration_classes_are_distinct_and_safe(monkeypatch):
    assert DevelopmentConfig.DEBUG is True
    assert TestingConfig.TESTING is True
    assert TestingConfig.WTF_CSRF_ENABLED is False
    assert ProductionConfig.SESSION_COOKIE_SECURE is True
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "development-only-secret")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app("production")


def test_dockerfile_runs_as_non_root_with_gunicorn():
    contents = (ROOT / "Dockerfile").read_text()
    assert "USER crm" in contents
    assert 'CMD ["gunicorn"' in contents
    assert "pip install --no-cache-dir" in contents
    assert ".env" in (ROOT / ".dockerignore").read_text().splitlines()


@pytest.mark.parametrize("filename", ["docker-compose.yml", "docker-compose.prod.yml"])
def test_compose_defines_persistent_healthy_postgres(filename):
    compose = yaml.safe_load((ROOT / filename).read_text())
    assert {"web", "db"}.issubset(compose["services"])
    database = compose["services"]["db"]
    assert "healthcheck" in database
    assert database["volumes"]
    assert "postgres_data" in compose["volumes"]
    web = compose["services"]["web"]
    assert "flask db upgrade" in web["command"]
    assert "gunicorn" in web["command"]


def test_production_compose_and_nginx_define_tls_proxy():
    compose = yaml.safe_load((ROOT / "docker-compose.prod.yml").read_text())
    assert "nginx" in compose["services"]
    assert "443:443" in compose["services"]["nginx"]["ports"]
    nginx = (ROOT / "nginx.conf").read_text()
    assert "listen 443 ssl" in nginx
    assert "ssl_certificate" in nginx
    assert "proxy_pass http://web:8000" in nginx


def test_operational_scripts_fail_closed_without_database_url():
    backup = (ROOT / "scripts" / "backup.sh").read_text()
    restore = (ROOT / "scripts" / "restore.sh").read_text()
    assert "${DATABASE_URL:?" in backup
    assert "${DATABASE_URL:?" in restore
    assert "pg_dump" in backup
    assert "pg_restore" in restore


def test_responsive_and_accessible_foundation(authenticated_client):
    response = authenticated_client.get("/")
    assert b'name="viewport"' in response.data
    assert b"Skip to main content" in response.data
    assert b'aria-label="Main navigation"' in response.data
    assert b"navbar-toggler" in response.data
