from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin

from .permissions import IsAuthorOrAdminOrReadOnly


class TagIngredientMixin(RetrieveModelMixin, ListModelMixin, GenericViewSet):

    permission_classes = (IsAuthorOrAdminOrReadOnly,)
    pagination_class = None
