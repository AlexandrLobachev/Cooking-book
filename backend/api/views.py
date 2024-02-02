import io

from django.http import FileResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.db.models import Exists, OuterRef
from djoser.views import UserViewSet

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
    RecipeReadSerializer,
    RecipeWriteSerializer,
    FollowSerializer,
)
from .filters import RecipeFilter, IngredientFilter
from .mixins import TagIngredientMixin
from .intermediate import del_intermediate_obj, add_intermediate_obj

User = get_user_model()


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

    def add_or_del_recipe(self, request, pk, model):
        """Добавляет или удаляет рецепт в избранное или список покупок."""
        if request.method == 'POST':
            return add_intermediate_obj(request, pk, model)
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
            ingredient = row.get('ingredient__name').capitalize()
            measurement_unit = row.get('ingredient__measurement_unit')
            amount = row.get('amount__sum')
            out.write(f'\n{ingredient}({measurement_unit}) - {amount}')
        content = out.getvalue()
        out.close()
        return FileResponse(
            content,
            headers={
                'Content-Type': 'text/plain',
                'Content-Disposition': 'attachment;'
                                       'filename="shopping_cart.txt"',
            }
        )


class UserCustomViewSet(UserViewSet):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return User.objects.all()
        return User.objects.annotate(
            is_subscribed=Exists(Follow.objects.filter(
                following=OuterRef('pk'),
                user=self.request.user,
            )))

    def get_followings(self, request):
        return User.objects.prefetch_related(
            'recipes').annotate(
            is_subscribed=Exists(Follow.objects.filter(
                following=OuterRef('pk'),
                user=request.user
            )))

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,),
    )
    def me(self, request):
        """Переопределен из-за требований ТЗ.

        Предусмотрен только метод GET,
        также необходимо ограничить доступ к эдпойнту только
        для авторизованных пользователей.
        """
        return super().me(request)

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
        get_object_or_404(User, pk=id)
        if request.method == 'POST':
            return add_intermediate_obj(request, id, Follow)
        return del_intermediate_obj(request, id, Follow)
