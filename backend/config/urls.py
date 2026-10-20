from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from config.views import health
from inventory.api import IngredientViewSet

router = DefaultRouter()
router.register("ingredients", IngredientViewSet, basename="ingredient")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/", include(router.urls)),
]
