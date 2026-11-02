"""One bakery must never see or change another bakery's data through the API."""

from collections.abc import Callable
from typing import Any

import pytest
from rest_framework.test import APIClient

from inventory.models import Ingredient
from organizations.models import Organization

URL = "/api/ingredients/"


@pytest.fixture
def b_flour(org_b: Organization) -> Ingredient:
    return Ingredient.objects.create(organization=org_b, name="B's secret flour")


@pytest.mark.django_db
def test_list_shows_only_my_bakerys_ingredients(
    client_a: APIClient, org_a: Organization, b_flour: Ingredient
) -> None:
    Ingredient.objects.create(organization=org_a, name="Flour")

    response = client_a.get(URL)

    assert response.status_code == 200
    assert [row["name"] for row in response.json()] == ["Flour"]


@pytest.mark.django_db
def test_cannot_read_another_bakerys_ingredient(client_a: APIClient, b_flour: Ingredient) -> None:
    response = client_a.get(f"{URL}{b_flour.pk}/")

    # 404, not 403: don't even reveal that the record exists.
    assert response.status_code == 404


@pytest.mark.django_db
def test_cannot_update_another_bakerys_ingredient(client_a: APIClient, b_flour: Ingredient) -> None:
    response = client_a.patch(f"{URL}{b_flour.pk}/", {"name": "stolen"}, format="json")

    assert response.status_code == 404
    b_flour.refresh_from_db()
    assert b_flour.name == "B's secret flour"


@pytest.mark.django_db
def test_cannot_delete_another_bakerys_ingredient(client_a: APIClient, b_flour: Ingredient) -> None:
    response = client_a.delete(f"{URL}{b_flour.pk}/")

    assert response.status_code == 404
    assert Ingredient.objects.filter(pk=b_flour.pk).exists()


@pytest.mark.django_db
def test_new_ingredients_go_to_my_bakery_even_if_the_request_names_another(
    client_a: APIClient, org_a: Organization, org_b: Organization
) -> None:
    response = client_a.post(URL, {"name": "Butter", "organization": org_b.pk}, format="json")

    assert response.status_code == 201
    assert Ingredient.objects.get(name="Butter").organization == org_a


@pytest.mark.django_db
def test_decimals_are_returned_as_exact_strings_not_floats(client_a: APIClient) -> None:
    client_a.post(URL, {"name": "Flour", "density_g_per_ml": "0.507210"}, format="json")

    row = client_a.get(URL).json()[0]

    assert row["density_g_per_ml"] == "0.507210"


@pytest.mark.django_db
def test_logged_out_requests_are_rejected() -> None:
    assert APIClient().get(URL).status_code == 403


@pytest.mark.django_db
def test_user_with_no_bakery_is_rejected(make_member: Callable[..., Any]) -> None:
    client = APIClient()
    client.force_login(make_member("loner"))

    assert client.get(URL).status_code == 403


@pytest.mark.django_db
class TestUserInSeveralBakeries:
    @pytest.fixture
    def client_ab(
        self, make_member: Callable[..., Any], org_a: Organization, org_b: Organization
    ) -> APIClient:
        client = APIClient()
        client.force_login(make_member("consultant", org_a, org_b))
        return client

    def test_header_picks_the_bakery(
        self, client_ab: APIClient, org_b: Organization, b_flour: Ingredient
    ) -> None:
        response = client_ab.get(URL, HTTP_X_ORGANIZATION=str(org_b.pk))

        assert [row["name"] for row in response.json()] == ["B's secret flour"]

    def test_missing_header_is_an_error_not_a_guess(self, client_ab: APIClient) -> None:
        assert client_ab.get(URL).status_code == 400

    def test_header_for_a_bakery_im_not_in_is_rejected(
        self, client_ab: APIClient, make_org: Callable[[str], Organization]
    ) -> None:
        other = make_org("Bakery C")

        assert client_ab.get(URL, HTTP_X_ORGANIZATION=str(other.pk)).status_code == 403

    def test_garbage_header_is_rejected(self, client_ab: APIClient) -> None:
        assert client_ab.get(URL, HTTP_X_ORGANIZATION="abc").status_code == 400
