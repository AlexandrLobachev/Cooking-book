from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework import status
from rest_framework.serializers import ValidationError

from users.models import Follow
from recipes.models import Favorite, ShopingCart
from .permissions import IsAuthorOrAdminOrReadOnly

User = get_user_model()


class DelIntermediateObjMixin():

    def del_intermediate_obj(self, request, pk, model):
        args_for_obj={
            Favorite: {'user':request.user, 'recipe':pk},
            ShopingCart: {'user':request.user, 'recipe':pk},
            Follow: {'user':request.user, 'following':pk},
        }
        messages = {
            Favorite: 'Рецепт отсутствует в избранном!',
            ShopingCart: 'Рецепт отсутствует в списке покупок!',
            Follow: 'У вас нет подписки на этого блогера!',
        }
        queryset_objs = model.objects.all()
        print(args_for_obj.get(model))
        try:
            obj = queryset_objs.get(**(args_for_obj.get(model)))
        except queryset_objs.model.DoesNotExist:
            raise ValidationError(messages.get(model))
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagIngredientMixin(RetrieveModelMixin, ListModelMixin, GenericViewSet):

    permission_classes = (IsAuthorOrAdminOrReadOnly,)
    pagination_class = None