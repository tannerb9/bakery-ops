from rest_framework import serializers

from inventory.models import Ingredient


class IngredientSerializer(serializers.ModelSerializer[Ingredient]):
    class Meta:
        model = Ingredient
        fields = ["id", "name", "density_g_per_ml", "grams_per_each", "created_at"]
        read_only_fields = ["id", "created_at"]
