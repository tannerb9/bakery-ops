from inventory.models import Ingredient
from inventory.serializers import IngredientSerializer
from organizations.api import OrgScopedViewSet


class IngredientViewSet(OrgScopedViewSet[Ingredient]):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
