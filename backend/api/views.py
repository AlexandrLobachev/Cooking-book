import io

from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.viewsets import ModelViewSet
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.db.models import Exists, OuterRef, Subquery
from djoser.views import UserViewSet
from rest_framework.serializers import ValidationError

from users.models import Follow

from recipes.models import (
    Ingredient,
    Tag,
    Recipe,
    Favorite,
    ShopingCart,
)
from .serializers import (
    IngredientSerializer,
    TagSerializer,
    UserSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
    RecipeForExtraActionsSerializer,
    FollowSerializer,
)
from .permissions import IsAuthorOrAdminOrReadOnly
from .filters import RecipeFilter, IngredientFilter
from .mixins import TagIngredientMixin, DelIntermediateObjMixin

User = get_user_model()


class IngredientViewSet(TagIngredientMixin):
    '''Вывод ингредиентов.'''

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class TagViewSet(TagIngredientMixin):
    '''Вывод тегов.'''

    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class RecipeViewSet(ModelViewSet, DelIntermediateObjMixin):
    """Вывод рецептов и корзины покупок."""

    queryset = Recipe.objects.all()
    serializer_class = RecipeReadSerializer
    permission_classes = (IsAuthorOrAdminOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'patch', 'partial_update']:
            return RecipeWriteSerializer
        return RecipeReadSerializer

    # def perform_create(self, serializer):
    #     serializer.save(author=self.request.user)

    def get_queryset(self):
        if self.request.user.is_authenticated:
            queryset = Recipe.objects.annotate(
                is_favorited=Exists(Favorite.objects.filter(
                    recipe=OuterRef('pk'),
                    user=self.request.user,
                )),
                is_in_shopping_cart=Exists(ShopingCart.objects.filter(
                    recipe=OuterRef('pk'),
                    user=self.request.user,
                ))
            )
            return queryset
        return Recipe.objects.all()

    def add_recipe(self, request, pk, model):
        """Добавляет рецепт в избранное или в корзину покупок."""
        queryset = self.get_queryset()
        try:
            recipe = queryset.get(pk=pk)
        except queryset.model.DoesNotExist:
            raise ValidationError('Рецепт не существует!')
        if model.objects.filter(user=request.user, recipe=recipe):
            raise ValidationError(
                f'Рецепт уже добавлен в {model._meta.verbose_name}!'
            )
        model.objects.create(user=request.user, recipe=recipe)
        serializer = RecipeForExtraActionsSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def add_or_del_recipe(self, request, pk, model):
        """Добавляет или удаляет рецепт в избранное или список покупок."""
        if request.method == 'POST':
            return self.add_recipe(request, pk, model)
        elif request.method == 'DELETE':
            get_object_or_404(Recipe, pk=pk)
            return self.del_intermediate_obj(request, pk, model)


    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='favorite',
        permission_classes=[IsAuthenticated, ]
    )
    def favorite(self, request, pk):
        return self.add_or_del_recipe(
            request, pk, Favorite
        )

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='shopping_cart',
        permission_classes=[IsAuthenticated, ]
    )
    def shopping_cart(self, request, pk):
        return self.add_or_del_recipe(
            request, pk, ShopingCart
        )

    @action(
        detail=False,
        methods=['get',],
        url_path='download_shopping_cart',
        permission_classes=[IsAuthenticated, ]
    )
    def download_shopping_cart(self, request):
        """Формирует список покупок и возвращает txt файл в ответе."""
        shopping_cart = self.queryset.filter(
            shopingcart__user=self.request.user
        ).values('ingredients__name', 'ingredients__measurement_unit'
        ).annotate(Sum('recipe_ingredient__amount'))
        out = io.StringIO()
        out.write('Список покупок:'"\n")
        for row in list(shopping_cart):
            out.write(
                f'\n{row.get("ingredients__name").capitalize()} '
                f'({row.get("ingredients__measurement_unit")}) - '
                f'{row.get("recipe_ingredient__amount__sum")}'
            )
        content = out.getvalue()
        out.close()
        return HttpResponse(
            content,
            headers={
            'Content-Type': 'text/plain',
            'Content-Disposition': 'attachment; filename="shopping_cart.txt"',
            }
        )


class UserCustomViewSet(UserViewSet, DelIntermediateObjMixin):
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

    def add_subscribe(self, request, id, following):
        """Добавляет подписку."""
        if request.user == following:
            raise ValidationError('Нельзя подписаться на себя!')
        if Follow.objects.filter(user=request.user, following=following):
            raise ValidationError('Нельзя дважды подписаться на одного блогера!')

        Follow.objects.create(
            user=request.user, following=following
        )
        following=User.objects.filter(pk=id).annotate(
            is_subscribed=Exists(Follow.objects.filter(
                following=OuterRef('pk'),
                user=request.user
            )))[0]
        serializer = FollowSerializer(
            following, context={'request': request})
        return Response(serializer.data,
                status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,),
    )

    def me(self, request):
        return super().me(request)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,),
    )

    def subscriptions(self, request):
        followings = User.objects.annotate(
                is_subscribed=Exists(Follow.objects.filter(
                    following=OuterRef('pk'),
                    user=self.request.user,
                ))).filter(following__user=self.request.user)
        page = self.paginate_queryset(followings)
        if page is not None:
            serializer = FollowSerializer(
                page, context={'request': request}, many=True
            )
            return self.get_paginated_response(serializer.data)

        serializer = FollowSerializer(
            followings, context={'request': request},  many=True
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
        return self.del_intermediate_obj(request, id, Follow)



