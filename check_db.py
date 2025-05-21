import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_marketplace.settings')
django.setup()

from django.db import connection
from marketplace.models import Offer

def check_db_structure():
    with connection.cursor() as cursor:
        # Получаем список всех колонок в таблице
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'marketplace_offer';
        """)
        columns = cursor.fetchall()
        
        print("Структура таблицы marketplace_offer:")
        for column in columns:
            print(f"- {column[0]} ({column[1]})")
        
        # Проверяем ограничения уникальности
        cursor.execute("""
            SELECT tc.constraint_name, kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name = 'marketplace_offer'
            AND tc.constraint_type = 'UNIQUE';
        """)
        unique_constraints = cursor.fetchall()
        
        print("\nОграничения уникальности:")
        for constraint in unique_constraints:
            print(f"- {constraint[0]}: {constraint[1]}")

if __name__ == '__main__':
    check_db_structure() 