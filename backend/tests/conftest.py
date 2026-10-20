from collections.abc import Callable
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from organizations.models import Membership, Organization

User = get_user_model()


@pytest.fixture
def make_org() -> Callable[[str], Organization]:
    def _make(name: str) -> Organization:
        return Organization.objects.create(name=name)

    return _make


@pytest.fixture
def make_member() -> Callable[..., Any]:
    def _make(username: str, *orgs: Organization, role: str = Membership.Role.OWNER) -> Any:
        user = User.objects.create_user(username=username, password="pw-not-used-in-tests")
        for org in orgs:
            Membership.objects.create(user=user, organization=org, role=role)
        return user

    return _make


@pytest.fixture
def org_a(make_org: Callable[[str], Organization]) -> Organization:
    return make_org("Bakery A")


@pytest.fixture
def org_b(make_org: Callable[[str], Organization]) -> Organization:
    return make_org("Bakery B")


@pytest.fixture
def client_a(make_member: Callable[..., Any], org_a: Organization) -> APIClient:
    client = APIClient()
    client.force_login(make_member("alice", org_a))
    return client
