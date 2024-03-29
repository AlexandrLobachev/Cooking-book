# Generated by Django 3.2.23 on 2024-01-23 19:53

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0004_alter_recipe_image'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='favorite',
            options={'verbose_name': 'рецепт в избранном', 'verbose_name_plural': 'рецепты в избранном'},
        ),
        migrations.AlterModelOptions(
            name='ingredientinrecipe',
            options={'verbose_name': 'ингредиент в рецепт', 'verbose_name_plural': 'Ингредиенты в рецепт'},
        ),
        migrations.AlterModelOptions(
            name='shopingcart',
            options={'verbose_name': 'рецепт в список покупок', 'verbose_name_plural': 'Рецепты в списке покупок'},
        ),
        migrations.AddField(
            model_name='recipe',
            name='created',
            field=models.DateTimeField(auto_now_add=True, db_index=True, default=django.utils.timezone.now, verbose_name='Дата добавления'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='ingredientinrecipe',
            name='ingredient',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='recipes.ingredient', verbose_name='Ингредиент'),
        ),
        migrations.AlterField(
            model_name='ingredientinrecipe',
            name='recipe',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipe_ingredient', to='recipes.recipe', verbose_name='Рецепт'),
        ),
        migrations.AlterField(
            model_name='recipe',
            name='image',
            field=models.ImageField(blank=True, default=None, null=True, upload_to='cats/images/', verbose_name='Фото'),
        ),
    ]
