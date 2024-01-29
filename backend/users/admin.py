from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth import get_user_model

from recipes.admin import (
    FavoriteInline,
    ShoppingCartInline
)
from .models import Follow


User = get_user_model()


class FollowInline(admin.TabularInline):
    model = Follow
    extra = 0
    fk_name = 'user'
    fields = (
        'following',
    )


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    list_filter = (
        'username',
        'email',
    )
    inlines = (
        FavoriteInline,
        ShoppingCartInline,
        FollowInline
    )
