"""Tenancy rules: every bakery's data is isolated (decision D17)."""

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from inventory.models import Ingredient
from organizations.models import Membership, Organization


def test_project_uses_a_custom_user_model() -> None:
    # Swapping the user model after the first migration is painful, so it is set from day one.
    assert settings.AUTH_USER_MODEL == "accounts.User"


@pytest.mark.django_db
def test_a_user_can_join_an_organization_only_once(org_a: Organization) -> None:
    user = get_user_model().objects.create_user(username="sam")
    Membership.objects.create(user=user, organization=org_a, role=Membership.Role.OWNER)

    with pytest.raises(IntegrityError):
        Membership.objects.create(user=user, organization=org_a, role=Membership.Role.MEMBER)


@pytest.mark.django_db
def test_for_org_returns_only_that_organizations_rows(
    org_a: Organization, org_b: Organization
) -> None:
    Ingredient.objects.create(organization=org_a, name="Flour")
    Ingredient.objects.create(organization=org_b, name="Sugar")

    names = list(Ingredient.objects.for_org(org_a).values_list("name", flat=True))

    assert names == ["Flour"]


@pytest.mark.django_db
def test_two_bakeries_can_each_have_an_ingredient_with_the_same_name(
    org_a: Organization, org_b: Organization
) -> None:
    Ingredient.objects.create(organization=org_a, name="Flour")
    Ingredient.objects.create(organization=org_b, name="Flour")

    assert Ingredient.objects.filter(name="Flour").count() == 2


@pytest.mark.django_db
def test_one_bakery_cannot_have_duplicate_ingredient_names_ignoring_case(
    org_a: Organization,
) -> None:
    Ingredient.objects.create(organization=org_a, name="Flour")

    with pytest.raises(IntegrityError):
        Ingredient.objects.create(organization=org_a, name="flour")


@pytest.mark.django_db
@pytest.mark.parametrize("field", ["density_g_per_ml", "grams_per_each"])
@pytest.mark.parametrize("bad_value", ["0", "-1.5"])
def test_conversion_factors_must_be_positive_when_set(
    org_a: Organization, field: str, bad_value: str
) -> None:
    with pytest.raises(IntegrityError):
        Ingredient.objects.create(organization=org_a, name="Flour", **{field: bad_value})


@pytest.mark.django_db
def test_conversion_factors_are_optional(org_a: Organization) -> None:
    ingredient = Ingredient.objects.create(organization=org_a, name="Flour")

    assert ingredient.density_g_per_ml is None
    assert ingredient.grams_per_each is None
