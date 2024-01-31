from rest_framework import permissions


class IsAuthorOrAdminOrReadOnly(permissions.IsAuthenticatedOrReadOnly):
    """Доступ на редактирование только для автора или админа."""

    def has_object_permission(self, request, view, recipe):
        return (request.method in permissions.SAFE_METHODS
                or recipe.author == request.user
                or request.user.is_staff)


class CurrentUserOrAdminOrReadOnly(permissions.IsAuthenticatedOrReadOnly):

    def has_permission(self, request, view):
        if '/users/me/' in request.path and not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, user):
        currentuser = request.user
        if user == currentuser:
            return True
        if '/users/me/' in request.path and not request.user.is_authenticated:
            return False
        return request.method in permissions.SAFE_METHODS or currentuser.is_staff
