import io

from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count
from django.db.models import Exists, OuterRef
from djoser.views import UserViewSet
from rest_framework.serializers import ValidationError

from users.models import Follow
from recipes.models import (
    Ingredient,
    Tag,
    Recipe,
    Favorite,
    ShopingCart,
    IngredientInRecipe,
)
from .permissions import IsAuthorOrAdminOrReadOnly
from .serializers import (
    IngredientSerializer,
    TagSerializer,
    UserSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
    FollowSerializer,
    FavoriteSerializer,
    ShopingCartSerializer,
)
from .filters import RecipeFilter, IngredientFilter
from .mixins import TagIngredientMixin

User = get_user_model()


def del_intermediate_obj(request, pk, model):
    args_for_obj = {
        Favorite: {'user': request.user, 'recipe': pk},
        ShopingCart: {'user': request.user, 'recipe': pk},
        Follow: {'user': request.user, 'following': pk},
    }
    messages = {
        Favorite: 'Рецепт отсутствует в избранном!',
        ShopingCart: 'Рецепт отсутствует в списке покупок!',
        Follow: 'У вас нет подписки на этого блогера!',
    }
    queryset_objs = model.objects.all()
    try:
        obj = queryset_objs.get(**(args_for_obj.get(model)))
    except queryset_objs.model.DoesNotExist as err:
        raise ValidationError(messages.get(model)) from err
    obj.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


class IngredientViewSet(TagIngredientMixin):
    """Вывод ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class TagViewSet(TagIngredientMixin):
    """Вывод тегов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class RecipeViewSet(ModelViewSet):
    """Вывод рецептов и корзины покупок."""

    queryset = Recipe.objects.all()
    serializer_class = RecipeReadSerializer
    permission_classes = (IsAuthorOrAdminOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'patch', 'partial_update',):
            return RecipeWriteSerializer
        return RecipeReadSerializer

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Recipe.objects.all()
        return Recipe.objects.select_related(
            'author').prefetch_related(
            'tags', 'recipeingredients__ingredient').annotate(
            is_favorited=Exists(Favorite.objects.filter(
                recipe=OuterRef('pk'),
                user=self.request.user,
            )),
            is_in_shopping_cart=Exists(ShopingCart.objects.filter(
                recipe=OuterRef('pk'),
                user=self.request.user,
            ))
        )

    def add_recipe(self, request, pk, model):
        """Добавляет рецепт в избранное или в корзину покупок."""
        map = {Favorite: FavoriteSerializer,
               ShopingCart: ShopingCartSerializer,
               }
        data = {'user': request.user.pk, 'recipe': pk, }
        context = {'request': request}
        serializer = map.get(model)(data=data, context=context)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer.save()
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    def add_or_del_recipe(self, request, pk, model):
        """Добавляет или удаляет рецепт в избранное или список покупок."""
        if request.method == 'POST':
            return self.add_recipe(request, pk, model)
        if request.method == 'DELETE':
            get_object_or_404(Recipe, pk=pk)
            return del_intermediate_obj(request, pk, model)

    @action(
        detail=True,
        methods=('post', 'delete'),
        url_path='favorite',
        permission_classes=(IsAuthenticated,)
    )
    def favorite(self, request, pk):
        return self.add_or_del_recipe(
            request, pk, Favorite
        )

    @action(
        detail=True,
        methods=('post', 'delete',),
        url_path='shopping_cart',
        permission_classes=(IsAuthenticated,)
    )
    def shopping_cart(self, request, pk):
        return self.add_or_del_recipe(
            request, pk, ShopingCart
        )

    @action(
        detail=False,
        methods=('get',),
        url_path='download_shopping_cart',
        permission_classes=(IsAuthenticated,)
    )
    def download_shopping_cart(self, request):
        """Формирует список покупок и возвращает txt файл в ответе."""
        shopping_cart = IngredientInRecipe.objects.filter(
            recipe__shopingcart__user=self.request.user).values(
            'ingredient__name', 'ingredient__measurement_unit').annotate(
            Sum('amount'))
        out = io.StringIO()
        out.write('Список покупок:''\n')
        for row in list(shopping_cart):
            ingredient = row.get("ingredient__name").capitalize()
            measurement_unit = row.get("ingredient__measurement_unit")
            amount = row.get("amount__sum")
            out.write(f'\n{ingredient}({measurement_unit}) - {amount}')
        content = out.getvalue()
        out.close()
        return HttpResponse(
            content,
            headers={
                'Content-Type': 'text/plain',
                'Content-Disposition': 'attachment;'
                                       'filename="shopping_cart.txt"',
            }
        )


class UserCustomViewSet(UserViewSet):
    serializer_class = UserSerializer

    def get_queryset(self):
        if self.request.user.is_authenticated:
            queryset = User.objects.annotate(
                is_subscribed=Exists(Follow.objects.filter(
                    following=OuterRef('pk'),
                    user=self.request.user,
                )))
            return queryset
        return User.objects.all()

    def get_followings(self, request):
        return User.objects.prefetch_related(
            'recipes').annotate(
            is_subscribed=Exists(Follow.objects.filter(
                following=OuterRef('pk'),
                user=request.user
            )),
            recipes_count=Count('recipes'))

    def add_subscribe(self, request, id, following):
        """Добавляет подписку."""
        if request.user == following:
            raise ValidationError('Нельзя подписаться на себя!')
        if Follow.objects.filter(user=request.user, following=following):
            raise ValidationError(
                'Нельзя дважды подписаться на одного блогера!')

        Follow.objects.create(
            user=request.user, following=following
        )
        following = self.get_followings(request).filter(pk=id)[0]
        serializer = FollowSerializer(
            following, context={'request': request})
        return Response(serializer.data,
                        status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,),
    )
    def subscriptions(self, request):
        followings = self.get_followings(request).filter(
            following__user=self.request.user)
        page = self.paginate_queryset(followings)
        if page is not None:
            serializer = FollowSerializer(
                page, context={'request': request}, many=True
            )
            return self.get_paginated_response(serializer.data)

        serializer = FollowSerializer(
            followings, context={'request': request}, many=True
        )
        return Response(serializer.data)

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,),
    )
    def subscribe(self, request, id):
        following = get_object_or_404(User, pk=id)
        if request.method == 'POST':
            return self.add_subscribe(request, id, following)
        return del_intermediate_obj(request, id, Follow)
