from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager as BaseUserManager
from django.core.validators import MinValueValidator
from django.urls import reverse
import random
import string

def generate_activation_code():
    return '-'.join(
        ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        for _ in range(4)
    )

class CustomUserManager(BaseUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')  # Автоматически устанавливаем роль админа

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        if extra_fields.get('role') != 'admin':
            raise ValueError('Superuser must have role=admin.')

        return self._create_user(username, email, password, **extra_fields)

class User(AbstractUser):
    """
    Расширенная модель пользователя с дополнительными полями
    """
    ROLES = (
        ('client', 'Клиент'),
        ('manager', 'Менеджер'),
        ('admin', 'Администратор'),
    )
    
    role = models.CharField(max_length=10, choices=ROLES, default='client')
    phone_number = models.CharField(max_length=15, blank=True)
    middle_name = models.CharField(max_length=150, blank=True)

    objects = CustomUserManager()

class Market(models.Model):
    """
    Модель маркета (источника товаров)
    """
    name = models.CharField(max_length=100)
    url = models.URLField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    api_key = models.CharField(max_length=255, blank=True, help_text="API ключ для доступа к API маркета")
    api_url = models.URLField(blank=True, help_text="URL API маркета")
    search_url_template = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="Шаблон URL для поиска товара (используйте {query} для подстановки запроса)"
    )
    spider_name = models.CharField(max_length=50, blank=True, null=True, help_text="Имя Scrapy паука для парсинга этого маркета")

    def __str__(self):
        return self.name

    def search_products(self, query):
        """
        Поиск товаров в маркете по названию
        Возвращает список найденных предложений в формате:
        [
            {
                'name': 'Название товара',
                'price': 'Цена',
                'url': 'URL товара'
            },
            ...
        ]
        """
        # This method is now largely deprecated with the Scrapy integration
        # but kept for potential fallback or other uses.
        print(f"Warning: Using deprecated search_products method for market {self.name}")
        
        if not self.search_url_template and not (self.api_url and self.api_key):
            print(f"No search URL template or API configured for market {self.name}")
            return []
            
        try:
            import requests
            from bs4 import BeautifulSoup
            import json

            # Если есть API
            if self.api_url and self.api_key:
                headers = {'Authorization': f'Bearer {self.api_key}'}
                response = requests.get(
                    self.api_url,
                    params={'q': query},
                    headers=headers
                )
                # Assuming the API returns a list of dictionaries with 'name', 'price', 'url'
                return response.json()

            # Если есть шаблон поиска, используем его (базовый парсинг)
            if self.search_url_template:
                search_url = self.search_url_template.format(query=query)
                response = requests.get(search_url)
                response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                
                # Basic parsing example (needs customization per market)
                # This part is highly dependent on the market's HTML structure
                # For now, it just fetches the page.
                print(f"Fetched URL: {search_url}. Manual parsing logic needed here.")
                return [] # Return empty list as manual parsing is not implemented

        except requests.exceptions.RequestException as e:
            print(f"Error during request for market {self.name}: {e}")
            return []
        except json.JSONDecodeError:
             print(f"Error decoding JSON from API response for market {self.name}.")
             return []
        except Exception as e:
            print(f"An unexpected error occurred during search in market {self.name}: {e}")
            return []

class Product(models.Model):
    """
    Модель товара
    """
    name = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='products/', blank=True)
    platform_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Цена товара на нашей платформе",
        default=0.00
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    popularity = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_min_price(self):
        """Получить минимальную цену среди всех предложений (из FakeOffer)"""
        offer = self.fake_offers.order_by('price').first()
        return offer.price if offer else None

    def get_absolute_url(self):
        """Получить URL для просмотра товара"""
        return reverse('product_detail', kwargs={'pk': self.pk})

class Offer(models.Model):
    """
    Модель предложения (оффера) на товар от определенного маркета
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='offers')
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    url = models.URLField(max_length=500, unique=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'market', 'url')

    def __str__(self):
        return f"{self.product.name} - {self.market.name} ({self.price} руб.)"

    def get_absolute_url(self):
        """Получить URL для просмотра предложения"""
        return reverse('product_detail', kwargs={'pk': self.product.pk})

class Cart(models.Model):
    """
    Модель корзины пользователя
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'offer')

class Receipt(models.Model):
    """
    Модель чека (истории покупок)
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_date = models.DateTimeField(auto_now_add=True)
    activation_code = models.CharField(max_length=32, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.activation_code:
            self.activation_code = generate_activation_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Receipt #{self.id} - {self.user.username}"

class FakeOffer(models.Model):
    price = models.DecimalField(decimal_places=2, max_digits=10)
    url = models.URLField(max_length=500)
    title = models.CharField(blank=True, max_length=255, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    market = models.ForeignKey('Market', on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='fake_offers')

    def __str__(self):
        return f"{self.title or ''} ({self.price} руб.)"
