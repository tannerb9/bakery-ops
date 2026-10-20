"""Guardrails that keep the tenancy rule from being bypassed by accident."""

from collections.abc import Iterator
from typing import Any

from django.apps import apps
from django.urls import URLPattern, URLResolver, get_resolver

from organizations.api import OrgScopedViewSet
from organizations.models import OrgOwnedModel


def _iter_views(patterns: list[Any]) -> Iterator[Any]:
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            yield from _iter_views(pattern.url_patterns)
        elif isinstance(pattern, URLPattern):
            yield pattern.callback


def test_every_api_view_over_bakery_data_is_org_scoped() -> None:
    offenders = []
    for callback in _iter_views(get_resolver().url_patterns):
        view_class = getattr(callback, "cls", None)
        queryset = getattr(view_class, "queryset", None)
        model = getattr(queryset, "model", None)
        if model and issubclass(model, OrgOwnedModel):
            if not issubclass(view_class, OrgScopedViewSet):  # type: ignore[arg-type]
                offenders.append(view_class.__name__)  # type: ignore[union-attr]

    assert offenders == []


def test_every_bakery_owned_model_uses_the_org_scoped_base() -> None:
    # Any concrete model with an `organization` field must inherit OrgOwnedModel,
    # so it gets `.for_org()` and is covered by the guardrail above.
    offenders = [
        model.__name__
        for model in apps.get_models()
        if any(f.name == "organization" for f in model._meta.fields)
        and not issubclass(model, OrgOwnedModel)
        and model._meta.app_label != "organizations"
    ]

    assert offenders == []
