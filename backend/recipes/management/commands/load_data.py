import csv
import json

from django.core.management.base import BaseCommand
from django.db import transaction

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Поместите файлы в директорию static/load_data/'
    directory_path = r'static/data/'

    def create_ingredient(self, dict):
        """Создает объект класса Ingredient."""
        Ingredient.objects.get_or_create(**dict)

    def json_to_dicts(self, file: str) -> list[dict]:
        """Возвращает список словарей, из JSON файла."""
        with open(file, encoding='utf-8') as json_file:
            list_of_dicts = json.load(json_file)
            return list_of_dicts

    def csv_to_dicts(self, file: str) -> list[dict]:
        """Возвращает список словарей из CSV файла."""
        with open(file, encoding='utf-8') as r_file:
            reader = csv.reader(r_file, delimiter=',')
            print(reader)
            list_of_dicts = []
            for row in reader:
                dict = {'name': row[0], 'measurement_unit': row[1]}
                list_of_dicts.append(dict)
            return list_of_dicts

    def iterator(self, list_of_dicts: list[dict]):
        """Перебирает список словарей и передает их для создания объектов."""
        import_counter = 0
        for dict in list_of_dicts:
            self.create_ingredient(dict)
            import_counter += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Импортировано {import_counter} объектов.'
            ))

    def add_arguments(self, parser):
        parser.add_argument('type_file', type=str,
                            help='Введите тип расширения файла csv или json.'
                                 'Например load_data csv')

    @transaction.atomic
    def handle(self, *args, **options):
        type_file = options['type_file']
        file = f'{self.directory_path}ingredients.{type_file}'
        if type_file == 'json':
            list_of_dicts = self.json_to_dicts(file)
        elif type_file == 'csv':
            list_of_dicts = self.csv_to_dicts(file)
        else:
            self.stdout.write(
                'Введен некоректный тип расширения. Только csv или json.')
            exit()
        self.iterator(list_of_dicts)
        self.stdout.write(self.style.SUCCESS('Импорт завершен!'))
