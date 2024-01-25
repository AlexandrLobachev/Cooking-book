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

class IngredientSerializer(ModelSerializer):

    class Meta:
        fields = ('__all__')
        model = Ingredient


class RecipeIngredientSerializer(ModelSerializer):
    id = ReadOnlyField(source='ingredient.id')
    name = ReadOnlyField(source='ingredient.name')
    measurement_unit = ReadOnlyField(
        source='ingredient.measurement_unit'
    )
    # Убрать поле амоунт
    amount = IntegerField()

    class Meta:
        fields = ('id', 'name', 'measurement_unit', 'amount',)
        model = IngredientInRecipe

class IngredientInRecipeCreateSerializer(ModelSerializer):
    # УБРАТЬ ПОЛЯ ИЛИ Нормально оформит!
    id = IntegerField(write_only=True)
    amount = IntegerField(write_only=True)

    class Meta:
        fields = ('id', 'amount',)
        model = IngredientInRecipe

    def validate_amount(self, data):
        if data < 1:
            raise ValidationError('Количество не может быть меньше одного!')
        return data

class TagSerializer(ModelSerializer):

    class Meta:
        fields = ('__all__')
        model = Tag


class UserSerializer(ModelSerializer):
    """Вывод данных пользователя"""
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
        user = User(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name = validated_data['first_name'],
            last_name = validated_data['last_name'],
            password=validated_data['password'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class RecipeForExtraActionsSerializer(ModelSerializer):
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        fields = (
            'id',
            'name',
            'image',
            'cooking_time',
        )
        model = Recipe


class RecipeReadSerializer(ModelSerializer):
    tags = TagSerializer(read_only=True, many=True)
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(many=True, source='recipe_ingredient')
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
    """Сериализатор создания и редактирования произведения."""

    tags = PrimaryKeyRelatedField(
        required=True, many=True, queryset=Tag.objects.all()
    )
    author = HiddenField(default=CurrentUserDefault())
    ingredients = IngredientInRecipeCreateSerializer(
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
        data['ingredients'] = self.validate_ingredients(data.get('ingredients'))
        data['tags'] = self.validate_tags(data.get('tags'))
        data['cooking_time'] = self.validate_cooking_time(data.get('cooking_time'))
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

        recipe = Recipe.objects.create(
            author=validated_data['author'],
            cooking_time=validated_data['cooking_time'],
            text=validated_data['text'],
            name=validated_data['name'],
            image=validated_data['image'],
        )
        self.add_tags_to_recipe(recipe, validated_data['tags'])
        self.add_ingredients_to_recipe(recipe, validated_data['ingredients'])
        return recipe

    def update(self, instance, validated_data):
        instance.cooking_time = validated_data.get('cooking_time', instance.cooking_time)
        instance.text = validated_data.get('text', instance.text)
        instance.name = validated_data.get('name', instance.name)
        instance.image = validated_data.get('image', instance.image)
        self.add_tags_to_recipe(instance, validated_data['tags'])
        IngredientInRecipe.objects.filter(recipe=instance).delete()
        self.add_ingredients_to_recipe(instance, validated_data['ingredients'])
        instance.save()
        return instance

    def to_representation(self, instance):
        return RecipeReadSerializer(instance).data


class SubscriptionsSerializer(UserSerializer):
    recipes = SerializerMethodField()
    recipes_count = SerializerMethodField()

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


    def get_recipes_queryset(self, obj):
        # Добавить это в аннотацию и кверисет
        return Recipe.objects.filter(author=obj)

    def get_recipes(self, obj):
        try:
            query_params = self.context.get('request').query_params
            recipes_limit = int(query_params.get('recipes_limit'))
        except:
            recipes_limit = None
        return RecipeForExtraActionsSerializer(
            self.get_recipes_queryset(obj)[:recipes_limit],
            many=True).data

    def get_recipes_count(self, obj):
        # Добавить это в аннотацию и кверисет
        return self.get_recipes_queryset(obj).count()