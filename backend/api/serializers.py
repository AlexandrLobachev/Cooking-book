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
    PrimaryKeyRelatedField,
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
)

User = get_user_model()


class Base64ImageField(ImageField):

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name=f'temp.{ext}')

        return super().to_internal_value(data)


class TagSerializer(ModelSerializer):

    class Meta:
        fields = ('__all__')
        model = Tag


class IngredientSerializer(ModelSerializer):

    class Meta:
        fields = ('__all__')
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
    amount = IntegerField()

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'amount',)

    def validate_amount(self, data):
        if data < 1:
            raise ValidationError('Количество не может быть меньше одного!')
        return data


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
            'password',
            'is_subscribed',
        )
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


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
    recipes_count = IntegerField()

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
        try:
            query_params = self.context.get('request').query_params
            recipes_limit = int(query_params.get('recipes_limit'))
        except:
            recipes_limit = None
        return RecipeForExtraActionsSerializer(
            obj.recipes.all()[:recipes_limit],
            many=True).data


class RecipeReadSerializer(ModelSerializer):
    """Отображение рецепта с дополнительными полями."""
    tags = TagSerializer(read_only=True, many=True)
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True, source="recipeingredients"
    )
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


class RecipeWriteSerializer(ModelSerializer):
    """Сериализатор создания и редактирования рецепта."""

    tags = PrimaryKeyRelatedField(
        required=True, many=True, queryset=Tag.objects.all()
    )
    author = HiddenField(default=CurrentUserDefault())
    ingredients = AddIngredientToRecipeSerializer(
        required=True, many=True
    )
    image = Base64ImageField(required=True)

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
        if data is None or len(data) == 0:
            raise ValidationError('Укажите хотябы один тег!')
        tags_id = []
        for tag in data:
            if not Tag.objects.filter(id=tag.id).exists():
                raise ValidationError(
                    f'Тег с id {tag.id} не существует.'
                )
            if tag.id not in tags_id:
                tags_id.append(tag.id)
            else:
                raise ValidationError(
                    'Теги в вашем рецепте повторяются. '
                    'Проверьте и устраните повторы.')
        return data

    def validate_ingredients(self, data):
        if data is None or len(data) == 0:
            raise ValidationError('Укажите хотябы один ингредиент!')
        ingredients_id = []
        for ingredient in data:
            if not Ingredient.objects.filter(id=ingredient['id']).exists():
                raise ValidationError(
                    f'Ингредиент с id {ingredient["id"]} не существует.'
                )
            if ingredient['id'] not in ingredients_id:
                ingredients_id.append(ingredient['id'])
            else:
                raise ValidationError(
                    'Ингредиенты в вашем рецепте повторяются. '
                    'Проверьте и устраните повторы.')
        return data

    def validate_cooking_time(self, data):
        if not 0 < data <= 1440:
            raise ValidationError(
                'Укажите реальное затрачиваемое время для '
                'приготовления в диапазоне от 1 до 1440 минут!')
        return data

    def validate(self, data):
        data['ingredients'] = self.validate_ingredients(
            data.get('ingredients'))
        data['tags'] = self.validate_tags(data.get('tags'))
        data['cooking_time'] = self.validate_cooking_time(
            data.get('cooking_time'))
        return data

    def add_ingredients_to_recipe(self,recipe, ingredients):
        for ingredient in ingredients:
            IngredientInRecipe.objects.create(
                ingredient_id=ingredient.get('id'),
                amount=ingredient.get('amount'),
                recipe=recipe
            )

    def add_tags_to_recipe(self,recipe, tags):
        recipe.tags.set(tags)

    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        self.add_tags_to_recipe(recipe, tags)
        self.add_ingredients_to_recipe(recipe, ingredients)
        return recipe

    def update(self, instance, validated_data):
        instance.cooking_time = validated_data.get(
            'cooking_time', instance.cooking_time)
        instance.text = validated_data.get('text', instance.text)
        instance.name = validated_data.get('name', instance.name)
        instance.image = validated_data.get('image', instance.image)
        self.add_tags_to_recipe(instance, validated_data['tags'])
        IngredientInRecipe.objects.filter(recipe=instance).delete()
        self.add_ingredients_to_recipe(
            instance, validated_data['ingredients'])
        instance.save()
        return instance

    def to_representation(self, instance):
        return RecipeReadSerializer(instance).data


