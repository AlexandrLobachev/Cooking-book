from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):

    email = models.EmailField(
        verbose_name='Электронная почта',
        max_length=254,
        unique=True
    )
    first_name = models.CharField(
        verbose_name='Имя',
        max_length=150,
    )
    last_name = models.CharField(
        verbose_name='Фамилия',
        max_length=150,
    )
    password = models.CharField(
        verbose_name='Пароль',
        max_length=150)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['password', 'username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


class Follow(models.Model):
    following = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Блогер',)
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик',)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['following', 'user'], name='unique_follow',
            ),
            models.CheckConstraint(
                check=~models.Q(user__exact=models.F('following')),
                name='user_not_following',
            ),
        ]

        verbose_name = 'подписку'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return self.following.username