from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Product, Offer

class UserRegistrationForm(UserCreationForm):
    username = forms.CharField(label='Логин')
    email = forms.EmailField(label='Email адрес')
    first_name = forms.CharField(label='Имя')
    last_name = forms.CharField(label='Фамилия')
    middle_name = forms.CharField(label='Отчество', required=False)
    phone_number = forms.CharField(label='Номер телефона', required=False)
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Подтверждение пароля', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'middle_name', 'phone_number', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.help_text = None

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'image', 'platform_price']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите название товара'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Введите описание товара',
                'rows': 4
            }),
            'platform_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
                'placeholder': 'Введите цену на платформе'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control'
            })
        }
        labels = {
            'name': 'Название',
            'description': 'Описание',
            'image': 'Изображение',
            'platform_price': 'Цена на платформе'
        }
        help_texts = {
            'platform_price': 'Укажите цену в рублях, по которой товар будет продаваться на нашей платформе'
        }

class OfferForm(forms.ModelForm):
    class Meta:
        model = Offer
        fields = ['product', 'market', 'price', 'url']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-control'
            }),
            'market': forms.Select(attrs={
                'class': 'form-control'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
                'placeholder': 'Введите цену'
            }),
            'url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите ссылку на товар'
            })
        }
        labels = {
            'product': 'Товар',
            'market': 'Маркет',
            'price': 'Цена',
            'url': 'Ссылка на товар'
        }
        help_texts = {
            'price': 'Укажите цену в рублях',
            'url': 'Укажите прямую ссылку на товар в магазине'
        }

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя пользователя'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Пароль'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.help_text = None 