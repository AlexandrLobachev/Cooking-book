from django.contrib import admin

from .models import (
    Recipe,
    Ingredient,
    Tag,
    Favorite,
    ShopingCart,
    IngredientInRecipe
)


class IngredientInRecipeInline(admin.TabularInline):
    model = Recipe.ingredients.through
    extra = 0
    fields = (
        'ingredient',
        'amount',
    )


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'author',
    )
    list_display_links = ('name',)
    list_filter = (
        'name',
        'author',
        'tags',
    )
    search_fields = (
        'id',
        'name',
        'author',
        'tags',
    )
    fields = (
        'id',
        'author',
        'created',
        'name',
        'tags',
        'cooking_time',
        'text',
        'image',
        'favorite_count'
    )
    readonly_fields = ('id', 'favorite_count', 'created',)
    inlines = (IngredientInRecipeInline,)

    def favorite_count(self, instance):
        return instance.favorite_set.count()
    favorite_count.short_description = 'Добавлено в избранное(количество)'


class FavoriteInline(admin.TabularInline):
    model = Favorite
    extra = 0
    fields = (
        'recipe',
    )


class ShopingCartInline(admin.TabularInline):
    model = ShopingCart
    extra = 0
    fields = (
        'recipe',
    )


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    model = Tag
    list_display = ('id', 'name', 'color', 'slug')
    list_display_links = ('name',)
    fields = ('id', 'name', 'color', 'slug')
    readonly_fields = ('id',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    model = Ingredient
    list_display = ('id', 'name', 'measurement_unit',)
    list_display_links = ('name',)
    list_filter = (
        'name',
    )
    search_fields = ('name', 'id')
    fields = ('id', 'name', 'measurement_unit',)
    readonly_fields = ('id',)


@admin.register(IngredientInRecipe)
class IngredientInRecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'ingredient', 'amount',)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe',)


@admin.register(ShopingCart)
class ShopingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe',)
