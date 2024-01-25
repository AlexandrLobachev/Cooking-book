from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()




class Tag(models.Model):
    name = models.CharField('Тег', max_length=20)
    color = models.CharField('Цвет тега', max_length=16)
    slug = models.SlugField(
        'Идентификатор',
        unique=True,
    )

    class Meta:
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name

class Ingredient(models.Model):
    name = models.CharField('Ингредиент', max_length=150)
    measurement_unit = models.CharField(
        verbose_name='Единица измерения',
        max_length = 150
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return f'{self.name}({self.measurement_unit})'

class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='reviews',
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Теги',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        verbose_name='Ингредиенты',
        related_name='ingredient',
        through='IngredientInRecipe'
    )
    name = models.CharField(
        'Название рецепта',
        max_length=200,
    )
    text = models.TextField(
        'Описание',
    )
    cooking_time = models.PositiveSmallIntegerField(
        'Время приготовления (в минутах)',
    )
    image = models.ImageField(
        verbose_name='Фото',
        upload_to='cats/images/',
    )
    created = models.DateTimeField(
        'Дата добавления',
        auto_now_add=True,
        db_index=True
    )

    class Meta:
        default_related_name = 'recipes'
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-created',)

    def __str__(self):
        return self.name

class IngredientInRecipe(models.Model):
    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name='Ингредиент',
        on_delete=models.CASCADE
    )
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт',
        on_delete=models.CASCADE,
        related_name='recipe_ingredient'
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество'
    )

    class Meta:
        verbose_name = 'ингредиент в рецепт'
        verbose_name_plural = 'Ингредиенты в рецепт'

    def __str__(self):
        return self.ingredient.name


class UserRecipeModel(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )

    class Meta:
        abstract = True

    def __str__(self):
        return self.recipe.name

class Favorite(UserRecipeModel):

    class Meta:
        verbose_name = 'рецепт в избранном'
        verbose_name_plural = 'рецепты в избранном'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'user'], name='unique_favorite',
            )]



class ShopingCart(UserRecipeModel):

    class Meta:
        verbose_name = 'рецепт в список покупок'
        verbose_name_plural = 'Рецепты в списке покупок'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'user'], name='unique_shopping_cart',
            )]

