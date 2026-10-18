import pytest
from django.test import Client
from django.test.utils import override_settings


@pytest.mark.django_db
def test_health_reports_ok_and_reaches_the_database(client: Client) -> None:
    response = client.get("/api/health/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.django_db
@override_settings(APP_NAME="Proof")
def test_brand_name_comes_from_the_single_app_name_setting(client: Client) -> None:
    response = client.get("/api/health/")

    assert response.json()["app"] == "Proof"


@pytest.mark.django_db
def test_runs_on_postgres_not_sqlite() -> None:
    from django.db import connection

    assert connection.vendor == "postgresql"
