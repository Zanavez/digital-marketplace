from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from .models import Product, Offer, Cart, Receipt, Market, User, FakeOffer
from django.contrib import messages
from .forms import UserRegistrationForm, ProductForm, OfferForm
from django.contrib.auth.views import LoginView
from django.urls import reverse
from .forms import CustomAuthenticationForm
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
import scrapy
import json
import subprocess
import sys
import os
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.template import RequestContext

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from twisted.internet import reactor
from django.db.models import ObjectDoesNotExist # Импортируем для более общего исключения
from django.db import transaction # Импортируем transaction для атомарности

# Assume this mapping exists or can be derived from Market model
MARKET_SPIDER_MAP = {
    '1': 'steam', # Assuming Market ID 1 is Steam
    # Add other markets and their spider names here
}

class HomeView(ListView):
    model = Product
    template_name = 'marketplace/home.html'
    context_object_name = 'products'
    paginate_by = 10

    def get_queryset(self):
        queryset = Product.objects.all()
        if self.request.user.is_authenticated and self.request.user.role == 'manager':
            # Для менеджеров показываем недавно добавленные товары
            queryset = queryset.order_by('-created_at')
        else:
            # Для остальных показываем популярные товары
            queryset = queryset.order_by('-popularity')
        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_manager'] = self.request.user.is_authenticated and self.request.user.role == 'manager'
        return context

class ProductListView(ListView):
    model = Product
    template_name = 'marketplace/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        query = self.request.GET.get('q')
        sort = self.request.GET.get('sort', '-popularity')
        
        products = Product.objects.all()
        
        if query:
            products = products.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query)
            )
        
        return products.order_by(sort)

class ProductDetailView(DetailView):
    model = Product
    template_name = 'marketplace/product_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        offers = self.object.offers.all().order_by('price')
        for offer in offers:
            offer.is_fake = hasattr(offer, 'fakeoffer_ptr') or offer.__class__.__name__ == 'FakeOffer'
        context['offers'] = offers
        return context

@login_required
def add_to_cart(request, offer_id):
    if request.user.role == 'manager':
        return redirect('home')
    offer = get_object_or_404(Offer, id=offer_id)
    if request.method != 'POST':
        return redirect('product_detail', pk=offer.product.id)
    
    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        offer=offer
    )
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    messages.success(request, 'Товар добавлен в корзину')
    return redirect('product_detail', pk=offer.product.id)

@login_required
def add_platform_to_cart(request, product_id):
    if request.user.role == 'manager':
        return redirect('home')
    product = get_object_or_404(Product, id=product_id)
    if request.method != 'POST':
        return redirect('product_detail', pk=product.id)
    
    # Создаем или получаем предложение от платформы
    platform_market, _ = Market.objects.get_or_create(
        name='Digital Marketplace',
        defaults={
            'url': request.build_absolute_uri('/'),
            'description': 'Наша платформа'
        }
    )
    
    platform_offer, _ = Offer.objects.get_or_create(
        product=product,
        market=platform_market,
        defaults={
            'price': product.platform_price,
            'url': request.build_absolute_uri(product.get_absolute_url())
        }
    )
    
    # Обновляем цену предложения, если она изменилась
    if platform_offer.price != product.platform_price:
        platform_offer.price = product.platform_price
        platform_offer.save()
    
    # Добавляем в корзину
    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        offer=platform_offer
    )
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    
    messages.success(request, 'Товар добавлен в корзину')
    return redirect('product_detail', pk=product.id)

@login_required
def cart_view(request):
    if request.user.role == 'manager':
        return redirect('home')
    cart_items = Cart.objects.filter(user=request.user)
    total = sum(item.offer.price * item.quantity for item in cart_items)
    return render(request, 'marketplace/cart.html', {
        'cart_items': cart_items,
        'total': total
    })

@login_required
def checkout(request):
    if request.user.role == 'manager':
        return redirect('home')
    cart_items = Cart.objects.filter(user=request.user)
    if not cart_items:
        messages.error(request, 'Корзина пуста')
        return redirect('cart')
    
    total = sum(item.offer.price * item.quantity for item in cart_items)
    return render(request, 'marketplace/checkout_confirm.html', {
        'cart_items': cart_items,
        'total': total
    })

@login_required
def checkout_confirm(request):
    if request.user.role == 'manager':
        return redirect('home')
    if request.method != 'POST':
        return redirect('checkout')
    
    cart_items = Cart.objects.filter(user=request.user)
    if not cart_items:
        messages.error(request, 'Корзина пуста')
        return redirect('cart')
    
    # Создаем чеки для каждого товара
    receipts = []
    for item in cart_items:
        receipt = Receipt.objects.create(
            user=request.user,
            offer=item.offer,
            quantity=item.quantity,
            total_price=item.offer.price * item.quantity
        )
        receipts.append(receipt)
    
    # Очищаем корзину
    cart_items.delete()
    
    # Если был куплен только один товар, перенаправляем на страницу чека
    if len(receipts) == 1:
        messages.success(request, 'Покупка успешно совершена!')
        return redirect('receipt_detail', pk=receipts[0].id)
    
    # Если было куплено несколько товаров, перенаправляем на историю покупок
    messages.success(request, 'Покупки успешно совершены!')
    return redirect('purchase_history')

@login_required
def receipt_detail(request, pk):
    if request.user.role == 'manager':
        return redirect('home')
    receipt = get_object_or_404(Receipt, pk=pk, user=request.user)
    return render(request, 'marketplace/receipt_detail.html', {
        'receipt': receipt
    })

@login_required
def purchase_history(request):
    if request.user.role == 'manager':
        return redirect('home')
    receipts = Receipt.objects.filter(user=request.user).order_by('-purchase_date')
    return render(request, 'marketplace/purchase_history.html', {
        'receipts': receipts
    })

# Представления для менеджера
class ManagerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'manager'

class ProductCreateView(ManagerRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'marketplace/product_form.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Товар успешно добавлен. Теперь вы можете добавить предложения от маркетов.')
        return redirect('offer_create', product=self.object.pk)

class ProductUpdateView(ManagerRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'marketplace/product_form.html'
    success_url = reverse_lazy('product_list')

    def form_valid(self, form):
        messages.success(self.request, 'Товар успешно обновлен')
        return super().form_valid(form)

class ProductDeleteView(ManagerRequiredMixin, DeleteView):
    model = Product
    template_name = 'marketplace/product_confirm_delete.html'
    success_url = reverse_lazy('home')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Товар успешно удален')
        return super().delete(request, *args, **kwargs)

class OfferCreateView(ManagerRequiredMixin, CreateView):
    model = Offer
    form_class = OfferForm
    template_name = 'marketplace/offer_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        product_id = self.kwargs.get('product')
        if product_id:
            product = get_object_or_404(Product, pk=product_id)
            initial['product'] = product
        return initial

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Если в initial есть product, значит, мы добавляем предложение к существующему товару
        if form.initial.get('product'):
            # Делаем поля ручного добавления необязательными
            if 'market' in form.fields:
                form.fields['market'].required = False
            if 'price' in form.fields:
                form.fields['price'].required = False
            if 'url' in form.fields:
                form.fields['url'].required = False
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context['form']
        
        # Если в initial есть product, значит, мы добавляем предложение к существующему товару
        if form.initial.get('product'):
            # Делаем поля ручного добавления необязательными
            if 'market' in form.fields:
                form.fields['market'].required = False
            if 'price' in form.fields:
                form.fields['price'].required = False
            if 'url' in form.fields:
                form.fields['url'].required = False
                
        context['form'] = form # Передаем измененную форму обратно в контекст
        context['markets'] = list(Market.objects.values('id', 'name'))
        context['create_offer_url_template'] = reverse('create_offer_from_search', kwargs={'product_id': 0}) # Используем 0 как placeholder
        return context

    def form_valid(self, form):
        # Проверяем, заполнены ли поля ручного добавления
        market = form.cleaned_data.get('market')
        price = form.cleaned_data.get('price')
        url = form.cleaned_data.get('url')

        if market and price and url:
            # Если поля ручного добавления заполнены, сохраняем форму
            response = super().form_valid(form)
            messages.success(self.request, 'Предложение успешно добавлено вручную')
            if 'add_another' in self.request.POST:
                return redirect('offer_create', product=form.instance.product.pk)
            return redirect('product_detail', pk=form.instance.product.pk)
        else:
            # Если поля ручного добавления не заполнены, но товар выбран,
            # предполагаем, что пользователь использует автоматический поиск.
            # В этом случае, основная форма не должна сохраняться.
            messages.info(self.request, 'Поля ручного добавления не заполнены. Используйте автоматический поиск или заполните все поля вручную.')
            # Перенаправляем обратно на ту же страницу, чтобы пользователь мог использовать поиск
            product_id = self.kwargs.get('product')
            if product_id:
                return redirect('offer_create', product=product_id)
            return redirect('offer_create') # Перенаправляем на общую страницу добавления, если product_id не был в URL

class OfferUpdateView(ManagerRequiredMixin, UpdateView):
    model = Offer
    template_name = 'marketplace/offer_form.html'
    fields = ['price', 'url']
    success_url = reverse_lazy('product_list')

class OfferDeleteView(ManagerRequiredMixin, DeleteView):
    model = Offer
    template_name = 'marketplace/offer_confirm_delete.html'
    
    def get_success_url(self):
        return reverse('product_detail', kwargs={'pk': self.object.product.pk})

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'customer' # Default role is customer
            user.save()
            messages.success(request, 'Вы успешно зарегистрированы!')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'marketplace/register.html', {'form': form})

class CustomLoginView(LoginView):
    template_name = 'marketplace/login.html'
    form_class = CustomAuthenticationForm
    
    def get_success_url(self):
        if self.request.user.is_staff:
            return reverse('admin:index')
        return reverse('home')

@csrf_exempt
def search_market_offers(request):
    import sys
    def all_fake_offers_debug():
        return [
            {
                'id': f.id,
                'product_id': f.product.id,
                'product_name': f.product.name,
                'market_id': f.market.id,
                'market_name': f.market.name,
                'title': f.title,
                'url': f.url
            }
            for f in FakeOffer.objects.all()
        ]
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print(f"[DEBUG] Raw data received: {data}", file=sys.stderr)
            product_id = data.get('product_id')
            market_ids = data.get('markets', [])
            print(f"[DEBUG] Retrieved market_ids: {market_ids}, Type: {type(market_ids)}", file=sys.stderr)
            print(f"[DEBUG] POST product_id={product_id}, market_ids={market_ids}", file=sys.stderr)
            if not product_id or not market_ids:
                return JsonResponse({'results': [], 'product_id': product_id, 'debug': 'no product_id or market_ids', 'all_fake_offers': all_fake_offers_debug()})
            
            # Поиск в обычных предложениях
            offers = Offer.objects.filter(product_id=product_id, market_id__in=[int(mid) for mid in market_ids])
            debug_ids = list(offers.values_list('id', flat=True))
            print(f"[DEBUG] Найдено Offer: {len(debug_ids)} ids={debug_ids}", file=sys.stderr)
            
            # Поиск в fake предложениях
            fake_offers = FakeOffer.objects.filter(product_id=product_id, market_id__in=[int(mid) for mid in market_ids])
            fake_debug_ids = list(fake_offers.values_list('id', flat=True))
            print(f"[DEBUG] Найдено FakeOffer: {len(fake_debug_ids)} ids={fake_debug_ids}", file=sys.stderr)
            
            results = []
            # Добавляем обычные предложения
            for offer in offers:
                results.append({
                    'market_id': str(offer.market.id),
                    'title': offer.title or f'Предложение ({offer.market.name})',
                    'url': offer.url,
                    'current_price': f'{offer.price} руб.',
                    'original_price': '',
                    'product_id': offer.product.id
                })
            
            # Добавляем fake предложения
            for offer in fake_offers:
                results.append({
                    'market_id': str(offer.market.id),
                    'title': offer.title or f'Предложение ({offer.market.name})',
                    'url': offer.url,
                    'current_price': f'{offer.price} руб.',
                    'original_price': '',
                    'product_id': offer.product.id
                })
                
            return JsonResponse({
                'results': results, 
                'product_id': product_id, 
                'debug': {
                    'market_ids': market_ids, 
                    'found_ids': debug_ids,
                    'found_fake_ids': fake_debug_ids
                }, 
                'all_fake_offers': all_fake_offers_debug()
            })
        except Exception as e:
            return JsonResponse({'error': f'Ошибка: {str(e)}'}, status=500)
    elif request.method == 'GET':
        product_id = request.GET.get('product_id')
        market_ids = request.GET.getlist('markets[]') or request.GET.getlist('markets')
        print(f"[DEBUG] Retrieved market_ids: {market_ids}, Type: {type(market_ids)}", file=sys.stderr)
        print(f"[DEBUG] GET product_id={product_id}, market_ids={market_ids}", file=sys.stderr)
        if not product_id or not market_ids:
            return JsonResponse({'results': [], 'product_id': product_id, 'debug': 'no product_id or market_ids', 'all_fake_offers': all_fake_offers_debug()})
        
        # Поиск в обычных предложениях
        offers = Offer.objects.filter(product_id=product_id, market_id__in=[int(mid) for mid in market_ids])
        debug_ids = list(offers.values_list('id', flat=True))
        print(f"[DEBUG] Найдено Offer: {len(debug_ids)} ids={debug_ids}", file=sys.stderr)
        
        # Поиск в fake предложениях
        fake_offers = FakeOffer.objects.filter(product_id=product_id, market_id__in=[int(mid) for mid in market_ids])
        fake_debug_ids = list(fake_offers.values_list('id', flat=True))
        print(f"[DEBUG] Найдено FakeOffer: {len(fake_debug_ids)} ids={fake_debug_ids}", file=sys.stderr)
        
        results = []
        # Добавляем обычные предложения
        for offer in offers:
            results.append({
                'market_id': str(offer.market.id),
                'title': offer.title or f'Предложение ({offer.market.name})',
                'url': offer.url,
                'current_price': f'{offer.price} руб.',
                'original_price': '',
                'product_id': offer.product.id
            })
        
        # Добавляем fake предложения
        for offer in fake_offers:
            results.append({
                'market_id': str(offer.market.id),
                'title': offer.title or f'Предложение ({offer.market.name})',
                'url': offer.url,
                'current_price': f'{offer.price} руб.',
                'original_price': '',
                'product_id': offer.product.id
            })
            
        return JsonResponse({
            'results': results, 
            'product_id': product_id, 
            'debug': {
                'market_ids': market_ids, 
                'found_ids': debug_ids,
                'found_fake_ids': fake_debug_ids
            }, 
            'all_fake_offers': all_fake_offers_debug()
        })
    else:
        return JsonResponse({'error': 'Разрешен только метод POST или GET'}, status=405)

@login_required
@require_POST
def create_offer_from_search(request, product_id):
    if request.user.role != 'manager':
        return JsonResponse({'error': 'Доступ запрещен.'}, status=403)

    # Теперь create_offer_from_search ожидает только реальный product_id
    try:
        with transaction.atomic():
            # Получаем существующий товар по product_id из URL
            product = get_object_or_404(Product, pk=product_id)
            print(f"Используем существующий товар: \"{product.name}\" (ID: {product.id})")

            market_id = request.POST.get('market_id')
            price_str = request.POST.get('price')
            url = request.POST.get('url')
            offer_title = request.POST.get('title')

            if not market_id or not price_str or not url:
                return JsonResponse({
                    'error': f'Неполные данные для создания предложения. market_id={market_id}, price={price_str}, url={url}, title={offer_title}'
                }, status=400)

            market = get_object_or_404(Market, pk=market_id)

            try:
                price_str_cleaned = price_str.replace(' руб.', '').replace(' ', '').replace(',', '.')
                price = float(price_str_cleaned)
            except ValueError:
                 return JsonResponse({'error': 'Неверный формат цены.'}, status=400)

            final_offer_title = offer_title if offer_title else f'Предложение для {product.name}'

            offer, created = Offer.objects.get_or_create(
                product=product,
                market=market,
                url=url,
                defaults={'price': price, 'title': final_offer_title}
            )

            if not created:
                updated = False
                if offer.price != price:
                    offer.price = price
                    updated = True
                if hasattr(offer, 'title') and offer.title != final_offer_title:
                     offer.title = final_offer_title
                     updated = True
                if updated:
                    offer.save()
                    print(f"Предложение обновлено: ID {offer.id}")
                else:
                    print(f"Предложение уже существует и не требует обновления: ID {offer.id}")
            else:
                print(f"Создано новое предложение: ID {offer.id}")

            return JsonResponse({'success': 'Предложение успешно создано/обновлено.', 'offer_id': offer.id})

    except Product.DoesNotExist:
        # Если товар не найден по переданному ID в URL
        return JsonResponse({'error': 'Товар не найден по указанному ID.'}, status=404)
    except Market.DoesNotExist:
        return JsonResponse({'error': 'Маркет не найден.'}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Произошла внутренняя ошибка сервера: {str(e)}'}, status=500)

@login_required
def remove_from_cart(request, item_id):
    if request.user.role == 'manager':
        return redirect('home')
    cart_item = get_object_or_404(Cart, id=item_id, user=request.user)
    cart_item.delete()
    messages.success(request, 'Товар удален из корзины')
    return redirect('cart')

@login_required
def delete_fake_offer(request, pk):
    offer = get_object_or_404(FakeOffer, pk=pk)
    product_id = offer.product.id
    if request.method == 'POST':
        offer.delete()
        messages.success(request, 'Предложение удалено.')
        return redirect('product_detail', pk=product_id)
    return render(request, 'marketplace/confirm_delete_fake_offer.html', {'offer': offer})

def get_cart_count(request):
    if request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role != 'manager':
        from .models import Cart
        return Cart.objects.filter(user=request.user).count()
    return 0

def cart_count_context(request):
    from .models import Cart
    if request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role != 'manager':
        return {'cart_count': Cart.objects.filter(user=request.user).count()}
    return {'cart_count': 0}
