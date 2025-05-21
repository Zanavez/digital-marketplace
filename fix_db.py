import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_marketplace.settings')
django.setup()

from django.db import connection
from marketplace.models import Offer

def check_and_fix_db():
    with connection.cursor() as cursor:
        # Проверяем существование колонки title
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'marketplace_offer' 
            AND column_name = 'title';
        """)
        has_title = cursor.fetchone()
        
        if not has_title:
            print("Колонка 'title' отсутствует. Добавляем...")
            try:
                cursor.execute("""
                    ALTER TABLE marketplace_offer 
                    ADD COLUMN title VARCHAR(255);
                """)
                print("Колонка 'title' успешно добавлена")
            except Exception as e:
                print(f"Ошибка при добавлении колонки: {e}")
        else:
            print("Колонка 'title' уже существует")

if __name__ == '__main__':
    check_and_fix_db() 