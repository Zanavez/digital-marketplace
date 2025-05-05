from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager as BaseUserManager
from django.core.validators import MinValueValidator
from django.urls import reverse

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
        if not self.search_url_template:
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
                return response.json()

            # Если есть шаблон поиска, используем его
            search_url = self.search_url_template.format(query=query)
            response = requests.get(search_url)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Здесь будет специфичная для каждого маркета логика парсинга
            # Пока возвращаем пустой список
            return []

        except Exception as e:
            print(f"Error searching in market {self.name}: {e}")
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
        """Получить минимальную цену среди всех предложений"""
        offer = self.offers.order_by('price').first()
        return offer.price if offer else None

    def get_absolute_url(self):
        """Получить URL для просмотра товара"""
        return reverse('product_detail', kwargs={'pk': self.pk})

class Offer(models.Model):
    """
    Модель предложения от конкретного маркета
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='offers')
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'market')

    def __str__(self):
        return f"{self.product.name} - {self.market.name} ({self.price})"

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

    def __str__(self):
        return f"Receipt #{self.id} - {self.user.username}"
