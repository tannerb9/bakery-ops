"""API base that scopes every request to the caller's active bakery."""

from __future__ import annotations

from typing import Any

from rest_framework import exceptions, viewsets
from rest_framework.request import Request
from rest_framework.serializers import BaseSerializer

from organizations.models import Membership, Organization, OrgOwnedModel, OrgScopedQuerySet

ORG_HEADER = "X-Organization"


def resolve_organization(request: Request) -> Organization:
    """Pick the bakery this request acts on.

    One membership: use it. Several: the X-Organization header must name one of them.
    Never guess, and never accept a bakery the user doesn't belong to.
    """
    user_id = request.user.pk
    if user_id is None:
        raise exceptions.NotAuthenticated()
    memberships = Membership.objects.filter(user_id=user_id).select_related("organization")
    orgs = {m.organization_id: m.organization for m in memberships}
    if not orgs:
        raise exceptions.PermissionDenied("You don't belong to any bakery yet.")

    header = request.headers.get(ORG_HEADER)
    if header is None:
        if len(orgs) == 1:
            return next(iter(orgs.values()))
        raise exceptions.ParseError(f"Send the {ORG_HEADER} header to choose a bakery.")

    try:
        org_id = int(header)
    except ValueError:
        raise exceptions.ParseError(f"{ORG_HEADER} must be a bakery id.") from None
    if org_id not in orgs:
        raise exceptions.PermissionDenied("You don't belong to that bakery.")
    return orgs[org_id]


class OrgScopedViewSet[M: OrgOwnedModel](viewsets.ModelViewSet[M]):
    """Every API view over bakery data must subclass this.

    Reads are filtered to the active bakery (other bakeries' rows 404), and new rows
    are always saved to the active bakery regardless of what the request body says.
    """

    organization: Organization

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        super().initial(request, *args, **kwargs)  # authentication + permissions first
        self.organization = resolve_organization(request)

    def get_queryset(self) -> OrgScopedQuerySet[M]:
        queryset = super().get_queryset()
        if not isinstance(queryset, OrgScopedQuerySet):
            raise TypeError(f"{type(self).__name__}.queryset must come from OrgOwnedModel.objects")
        return queryset.for_org(self.organization)

    def perform_create(self, serializer: BaseSerializer[M]) -> None:
        serializer.save(organization=self.organization)
