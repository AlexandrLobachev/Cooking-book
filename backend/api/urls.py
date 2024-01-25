from django.urls import include, path
from rest_framework import routers

from .views import (
    IngredientViewSet,
    TagViewSet,
    UserCustomViewSet,
    RecipeViewSet,
)

app_name = 'api'

router_review_v1 = routers.DefaultRouter()

router_review_v1.register('users', UserCustomViewSet, basename='user')
router_review_v1.register('ingredients', IngredientViewSet, basename='ingredient')
router_review_v1.register('tags', TagViewSet, basename='tag')
router_review_v1.register('recipes', RecipeViewSet, basename='recipe')

urlpatterns = [
    path('', include(router_review_v1.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
