from django_filters.rest_framework import (
    FilterSet,
    AllValuesMultipleFilter,
    BooleanFilter
)
from django.contrib.auth import get_user_model

from recipes.models import Recipe, Ingredient

User = get_user_model()


class RecipeFilter(FilterSet):
    tags = AllValuesMultipleFilter(field_name='tags__slug')
    is_favorited = BooleanFilter(method='enum_to_bool')
    is_in_shopping_cart = BooleanFilter(method='enum_to_bool')

    def enum_to_bool(self, queryset, name, filter_value):
        if not filter_value:
            return queryset
        if not self.request.user.is_authenticated:
            return Recipe.objects.none()
        return queryset.filter(**{name: filter_value})

    class Meta:
        model = Recipe
        fields = ('author',)


class IngredientFilter(FilterSet):

    class Meta:
        model = Ingredient
        fields = ('name',)
