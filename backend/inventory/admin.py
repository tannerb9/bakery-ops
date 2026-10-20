from django.contrib import admin

from inventory.models import Ingredient


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin[Ingredient]):
    list_display = ["name", "organization", "density_g_per_ml", "grams_per_each"]
    list_filter = ["organization"]
