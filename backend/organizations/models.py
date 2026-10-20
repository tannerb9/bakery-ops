"""Tenancy: every bakery is an Organization, and all bakery data belongs to exactly one."""

from __future__ import annotations

from typing import TypeVar

from django.conf import settings
from django.db import models

_T = TypeVar("_T", bound="OrgOwnedModel")


class Organization(models.Model):
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MEMBER = "member", "Member"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization"], name="unique_membership_per_org"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} @ {self.organization} ({self.role})"


class OrgScopedQuerySet(models.QuerySet[_T]):
    def for_org(self, organization: Organization) -> OrgScopedQuerySet[_T]:
        return self.filter(organization=organization)


class OrgOwnedModel(models.Model):
    """Base for every table that holds one bakery's data.

    Always read through `Model.objects.for_org(org)` in app code. API views must
    subclass `organizations.api.OrgScopedViewSet`; tests/test_architecture.py enforces both.
    """

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="+")

    objects = OrgScopedQuerySet.as_manager()

    class Meta:
        abstract = True
