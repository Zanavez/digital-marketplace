# Digital Marketplace

Современная платформа для агрегации и продажи цифровых товаров, разработанная на Django.

## Особенности

- 🛍️ Каталог цифровых товаров с поиском и фильтрацией
- 🔍 Автоматический поиск предложений на различных площадках
- 🛒 Удобная корзина покупок
- 📊 История покупок с детальными чеками
- 👤 Система пользователей с ролями (покупатель/менеджер)
- 🎨 Современный адаптивный дизайн
- 🌙 Темная тема

## Технологии

- Python 3.11
- Django 5.2
- Bootstrap 5
- PostgreSQL
- Font Awesome
- Crispy Forms

## Установка и запуск

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-username/digital-marketplace.git
cd digital-marketplace
```

2. Создайте виртуальное окружение и активируйте его:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
venv\Scripts\activate     # для Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Примените миграции:
```bash
python manage.py migrate
```

5. Создайте суперпользователя:
```bash
python manage.py createsuperuser
```

6. Запустите сервер разработки:
```bash
python manage.py runserver
```

## Структура проекта

```
digital_marketplace/  # Основной проект Django
├── settings.py      # Настройки проекта
└── urls.py         # Основные URL-маршруты

marketplace/        # Основное приложение
├── models.py      # Модели данных
├── views.py       # Представления
├── urls.py        # URL-маршруты приложения
├── forms.py       # Формы
└── templates/     # Шаблоны
    └── marketplace/
        ├── base.html
        ├── home.html
        └── ...
```

## Лицензия

MIT License 