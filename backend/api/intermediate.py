from rest_framework.response import Response
from rest_framework import status
from rest_framework.serializers import ValidationError

from users.models import Follow
from recipes.models import Favorite, ShoppingCart
from .serializers import (
    FavoriteSerializer,
    ShoppingCartSerializer,
    SubscribeSerializer,
)


def del_intermediate_obj(request, pk, model):
    args_for_obj = {
        Favorite: {'user': request.user, 'recipe': pk},
        ShoppingCart: {'user': request.user, 'recipe': pk},
        Follow: {'user': request.user, 'following': pk},
    }
    messages = {
        Favorite: 'Рецепт отсутствует в избранном!',
        ShoppingCart: 'Рецепт отсутствует в списке покупок!',
        Follow: 'У вас нет подписки на этого блогера!',
    }
    obj = model.objects.filter(**(args_for_obj.get(model)))
    if len(obj) == 0:
        raise ValidationError(messages.get(model))
    obj.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


def add_intermediate_obj(request, pk, model):
    map = {Favorite: (FavoriteSerializer, 'recipe'),
           ShoppingCart: (ShoppingCartSerializer, 'recipe'),
           Follow: (SubscribeSerializer, 'following'),
           }
    data = {'user': request.user.pk, map.get(model)[1]: pk, }
    context = {'request': request}
    serializer = map.get(model)[0](data=data, context=context)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(
        serializer.data,
        status=status.HTTP_201_CREATED
    )
