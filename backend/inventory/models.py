from django.db import models
from django.db.models.functions import Lower

from organizations.models import OrgOwnedModel


class Ingredient(OrgOwnedModel):
    """A raw ingredient (later also packaging) in one bakery's catalog.

    Conversion factors are optional; converting volume or "each" to grams without them
    raises instead of guessing (decision D19).
    """

    name = models.CharField(max_length=200)
    density_g_per_ml = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    grams_per_each = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"), "organization", name="unique_ingredient_name_per_org"
            ),
            models.CheckConstraint(
                condition=models.Q(density_g_per_ml__isnull=True)
                | models.Q(density_g_per_ml__gt=0),
                name="ingredient_density_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(grams_per_each__isnull=True) | models.Q(grams_per_each__gt=0),
                name="ingredient_grams_per_each_positive",
            ),
        ]

    def __str__(self) -> str:
        return self.name
