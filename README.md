#  Cooking Book
![workflow](https://github.com/AlexandrLobachev/cooking-book/actions/workflows/main.yml/badge.svg)

## Описание

Ресурс для любителей готовить. Пользователь может добавлять рецепты, прикреплять к ним фото
и просматривать рецепты других пользователей. Добвалять понравившиеся рецепты в избранное, а также 
добвалять рецепты в список покупок и выгружать список покупок.

[Ссылка на ресурс](https://diplom-lobachev.ddns.net/)

## Автор:

[Александр Лобачев](https://github.com/AlexandrLobachev/)

## Технологии используемые в проекте:

Python, Django, DRF, Nginx, Docker, Gunicorn, Github Actions

## Как запустить проект локально:

Для запуска на Windows вам потребуеться установить Docker и WSL.
Скачать можно с официального сайта и там же есть инструкции.

Клонировать репозиторий и перейти в него в командной строке:
```
git clone git@github.com:AlexandrLobachev/cooking-book.git
```
```
cd cooking-book
```
Создать файл .env и заполнить его(пример пример заполнения можно взять ниже):
```
POSTGRES_DB=cookbook
POSTGRES_USER=cookbook_user
POSTGRES_PASSWORD=cookbook_password
DB_HOST=db
DB_PORT=5432
SECRET_KEY='django-insecure-token-example3*$vmxm4)abgjw8000000000000000000000000'
DEBUG= True 
ALLOWED_HOSTS='127.0.0.1,localhost'
```
Создать образы и запустить контейнеры
```
docker compose up
```
Выполните миграции
```
docker compose exec backend python manage.py migrate
```
Соберите статические файлы
```
docker compose exec backend python manage.py collectstatic
```
Скопируйте статические файлы
```
docker compose exec backend cp -r /app/collected_static/. /backend_static/static/
```
Создать суперпользователя
```
docker compose -f docker-compose.yml exec backend python manage.py createsuperuser
```
Наполнить базу ингредиентами
```
docker compose -f docker-compose.yml exec backend python manage.py load_data csv
```
Проект доступен по адресу:
```
http://localhost/
```
