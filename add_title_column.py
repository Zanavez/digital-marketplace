import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_marketplace.settings')
django.setup()

from django.db import connection

def add_title_column():
    with connection.cursor() as cursor:
        try:
            # Добавляем колонку title
            cursor.execute("""
                ALTER TABLE marketplace_offer 
                ADD COLUMN title VARCHAR(255) DEFAULT '';
            """)
            print("Колонка 'title' успешно добавлена")
            
            # Обновляем существующие записи, устанавливая title равным product.name
            cursor.execute("""
                UPDATE marketplace_offer o
                SET title = p.name
                FROM marketplace_product p
                WHERE o.product_id = p.id;
            """)
            print("Существующие записи обновлены")
            
        except Exception as e:
            print(f"Ошибка: {e}")

if __name__ == '__main__':
    add_title_column() 