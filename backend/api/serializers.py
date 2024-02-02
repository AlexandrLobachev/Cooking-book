import base64

from rest_framework.fields import HiddenField
from rest_framework.validators import UniqueTogetherValidator
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework.serializers import (
    ImageField,
    ModelSerializer,
    IntegerField,
    ReadOnlyField,
    BooleanField,
    SerializerMethodField,
    ValidationError,
    CurrentUserDefault,
)

from recipes.models import (
    Ingredient,
    Tag,
    Recipe,
    IngredientInRecipe,
    Favorite,
    ShopingCart,
)
from users.models import Follow


User = get_user_model()


class Base64ImageField(ImageField):

    def to_internal_value(self, str_base64):
        if (isinstance(str_base64, str)
                and str_base64.startswith('data:image')):
            format, imgstr = str_base64.split(';base64,')
            ext = format.split('/')[-1]

            str_base64 = ContentFile(
                base64.b64decode(imgstr), name=f'temp.{ext}'
            )

        return super().to_internal_value(str_base64)


class TagSerializer(ModelSerializer):

    class Meta:
        fields = '__all__'
        model = Tag


class IngredientSerializer(ModelSerializer):

    class Meta:
        fields = '__all__'
        model = Ingredient


class RecipeIngredientSerializer(ModelSerializer):
    """Вывод ингредиентов в рецепте."""

    id = ReadOnlyField(source='ingredient.id')
    name = ReadOnlyField(source='ingredient.name')
    measurement_unit = ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        fields = ('id', 'name', 'measurement_unit', 'amount',)
        model = IngredientInRecipe


class AddIngredientToRecipeSerializer(ModelSerializer):
    """Добавление игнредиентов в рецепт."""

    id = IntegerField()
    amount = IntegerField(min_value=1)

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'amount',)


class UserSerializer(ModelSerializer):
    is_subscribed = BooleanField(read_only=True, default=False)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
        )


class RecipeForExtraActionsSerializer(ModelSerializer):
    """Отображение рецепта при подписке и добавлении в избранное."""

    class Meta:
        fields = (
            'id',
            'name',
            'image',
            'cooking_time',
        )
        model = Recipe


class FollowSerializer(UserSerializer):
    """Вывод подписок пользователя."""

    recipes = SerializerMethodField()
    recipes_count = ReadOnlyField(source='recipes.count')

    class Meta:
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'recipes',
            'is_subscribed',
            'recipes_count',
        )
        model = User

    def get_recipes(self, obj):
        query_params = self.context.get('request').query_params
        try:
            recipes_limit = int(query_params.get('recipes_limit'))
        except TypeError:
            recipes_limit = None
        return RecipeForExtraActionsSerializer(
            obj.recipes.all()[:recipes_limit],
            many=True).data


class RecipeReadSerializer(ModelSerializer):
    """Отображение рецепта с дополнительными полями."""

    tags = TagSerializer(read_only=True, many=True)
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True, source='recipeingredients'
    )
    image = SerializerMethodField(read_only=True)
    is_favorited = BooleanField(read_only=True, default=False)
    is_in_shopping_cart = BooleanField(read_only=True, default=False)

    class Meta:
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time',
            'is_favorited',
            'is_in_shopping_cart',
        )
        model = Recipe

    def get_image(self, obj):
        if obj.image:
            return obj.image.url
        return None


class RecipeWriteSerializer(ModelSerializer):
    """Сериализатор создания и редактирования рецепта."""

    author = HiddenField(default=CurrentUserDefault())
    ingredients = AddIngredientToRecipeSerializer(
        many=True, default=None
    )
    image = Base64ImageField(required=True)
    cooking_time = IntegerField(min_value=1, max_value=1440)

    class Meta:
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time',
        )
        model = Recipe
        validators = [
            UniqueTogetherValidator(
                queryset=Recipe.objects.all(),
                fields=('author', 'name', 'text'),
                message=(
                    'Вы уже публиковали рецепт с таким названием и описанием!'
                )
            )
        ]

    def validate_tags(self, data):
        if not data:
            raise ValidationError('Укажите хотябы один тег!')
        tags_id = [tag.id for tag in data]
        if len(tags_id) != len(set(tags_id)):
            raise ValidationError(
                'Теги в вашем рецепте повторяются. '
                'Проверьте и устраните повторы.')
        if len(tags_id) != len(Tag.objects.in_bulk(tags_id)):
            raise ValidationError('Указан не существующий тег!')
        return data

    def validate_ingredients(self, data):
        if not data:
            raise ValidationError('Укажите хотябы один ингредиент!')
        ingredients_id = [ingredient['id'] for ingredient in data]
        if len(ingredients_id) != len(set(ingredients_id)):
            raise ValidationError(
                'Ингредиенты в вашем рецепте повторяются. '
                'Проверьте и устраните повторы.')
        if (len(ingredients_id)
                != len(Ingredient.objects.in_bulk(ingredients_id))):
            raise ValidationError('Указан не существующий ингредиент!')
        return data

    def add_ingredients_to_recipe(self, recipe, ingredients):
        objs = [
            IngredientInRecipe(
                ingredient_id=ingredient.get('id'),
                amount=ingredient.get('amount'),
                recipe=recipe,
            )
            for ingredient in ingredients
        ]
        IngredientInRecipe.objects.bulk_create(objs)

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        recipe = super().create(validated_data)
        self.add_ingredients_to_recipe(recipe, ingredients)
        return recipe

    def update(self, recipe, validated_data):
        ingredients = validated_data.pop('ingredients', None)
        tags = validated_data.pop('tags', None)
        if tags is None or ingredients is None:
            raise ValidationError(
                'Указание тегов и ингредиентов обязательно!')
        recipe.ingredients.clear()
        self.add_ingredients_to_recipe(recipe, ingredients)
        recipe.tags.set(tags)
        return super().update(recipe, validated_data)

    def to_representation(self, instance):
        return RecipeReadSerializer(
            instance,
            context={'request': self.context.get('request')}
        ).data


class FavoriteSerializer(ModelSerializer):

    class Meta:
        fields = ('recipe', 'user',)
        model = Favorite
        validators = [
            UniqueTogetherValidator(
                queryset=model.objects.all(),
                fields=('recipe', 'user'),
                message='Рецепт уже в избранном',
            )
        ]

    def to_representation(self, instance):
        return RecipeForExtraActionsSerializer(
            instance.recipe,
            context={'request': self.context.get('request')}
        ).data


class ShopingCartSerializer(FavoriteSerializer):

    class Meta:
        fields = ('recipe', 'user',)
        model = ShopingCart
        validators = [
            UniqueTogetherValidator(
                queryset=model.objects.all(),
                fields=('recipe', 'user'),
                message='Рецепт уже в списке покупок',
            )
        ]


class SubscribeSerializer(ModelSerializer):

    class Meta:
        fields = ('following', 'user',)
        model = Follow
        validators = [
            UniqueTogetherValidator(
                queryset=model.objects.all(),
                fields=('following', 'user'),
                message='Нельзя дважды подписаться на одного блогера!',
            )
        ]

    def validate_following(self, data):
        request = self.context.get('request')
        user = request.user
        if user == data:
            raise ValidationError(
                'Нельзя подписаться на себя!')
        return data

    def to_representation(self, instance):
        return FollowSerializer(
            instance.following,
            context={'request': self.context.get('request')}
        ).data
