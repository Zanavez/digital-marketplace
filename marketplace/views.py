from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q
from .models import Product, Offer, Cart, Receipt, Market, User
from django.contrib import messages
from .forms import UserRegistrationForm, ProductForm, OfferForm
from django.contrib.auth.views import LoginView
from django.urls import reverse
from .forms import CustomAuthenticationForm
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string

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
        context['offers'] = self.object.offers.all().order_by('price')
        return context

@login_required
def add_to_cart(request, offer_id):
    if request.user.role == 'manager':
        return redirect('home')
    offer = get_object_or_404(Offer, id=offer_id)
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
            initial['product'] = get_object_or_404(Product, pk=product_id)
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['markets'] = Market.objects.all()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Предложение успешно добавлено')
        if 'add_another' in self.request.POST:
            return redirect('offer_create', product=form.instance.product.pk)
        return redirect('product_detail', pk=form.instance.product.pk)

class OfferUpdateView(ManagerRequiredMixin, UpdateView):
    model = Offer
    template_name = 'marketplace/offer_form.html'
    fields = ['price', 'url']
    success_url = reverse_lazy('product_list')

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Аккаунт успешно создан! Теперь вы можете войти.')
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

@login_required
@require_POST
def search_market_offers(request, product_id):
    if request.user.role != 'manager':
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    product = get_object_or_404(Product, pk=product_id)
    market_id = request.POST.get('market_id')
    
    if not market_id:
        return JsonResponse({'error': 'Не указан маркет'}, status=400)
    
    market = get_object_or_404(Market, pk=market_id)
    results = market.search_products(product.name)
    
    html = render_to_string('marketplace/includes/search_results.html', {
        'results': results,
        'product': product,
        'market': market
    })
    
    return JsonResponse({
        'html': html,
        'count': len(results)
    })

@login_required
@require_POST
def create_offer_from_search(request, product_id):
    if request.user.role != 'manager':
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    product = get_object_or_404(Product, pk=product_id)
    market_id = request.POST.get('market_id')
    price = request.POST.get('price')
    url = request.POST.get('url')
    
    if not all([market_id, price, url]):
        return JsonResponse({'error': 'Не все данные предоставлены'}, status=400)
    
    market = get_object_or_404(Market, pk=market_id)
    
    try:
        offer = Offer.objects.create(
            product=product,
            market=market,
            price=price,
            url=url
        )
        return JsonResponse({
            'success': True,
            'message': 'Предложение успешно создано',
            'offer_id': offer.id
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=400)

@login_required
def remove_from_cart(request, item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(Cart, id=item_id, user=request.user)
        cart_item.delete()
        messages.success(request, 'Товар успешно удален из корзины.')
    return redirect('cart')
