from rest_framework import permissions

class IsAuthorOrAdminOrReadOnly(permissions.IsAuthenticatedOrReadOnly):
    """Доступ на редактирование только для автора или админа."""

    def has_object_permission(self, request, view, obj):
        return (request.method in permissions.SAFE_METHODS
                or obj.author == request.user
                or request.user.is_staff)


class CurrentUserOrAdminOrReadOnly(permissions.IsAuthenticatedOrReadOnly):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if obj == user:
            return True
        return request.method in permissions.SAFE_METHODS or user.is_staff

