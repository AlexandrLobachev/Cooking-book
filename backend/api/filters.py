from django.db.models import Q
from django_filters.rest_framework import (
    FilterSet,
    CharFilter,
    BooleanFilter
)
from django.contrib.auth import get_user_model

from recipes.models import Recipe, Ingredient, Tag

User = get_user_model()


class RecipeFilter(FilterSet):
    tags = CharFilter(method='tags_filter')
    is_favorited = BooleanFilter(method='enum_to_bool')
    is_in_shopping_cart = BooleanFilter(method='enum_to_bool')

    def enum_to_bool(self, queryset, name, value):
        if self.request.user.is_authenticated:
            return queryset.filter(**{name: value})
        elif value is True and not self.request.user.is_authenticated:
             return Recipe.objects.none()
        else:
            return queryset

    def tags_filter(self, queryset, name, value):
        tags = self.request.query_params.getlist(name)
        if tags:
            condition = Q()
            for tag in tags:
                condition |= Q(tags__slug__icontains=tag)
            queryset = queryset.filter(condition)
        return queryset

    class Meta:
        model = Recipe
        fields = ('author',)


class IngredientFilter(FilterSet):

    class Meta:
        model = Ingredient
        fields = ('name',)
