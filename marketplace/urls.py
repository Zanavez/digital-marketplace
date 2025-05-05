from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Основные страницы
    path('', views.HomeView.as_view(), name='home'),
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('product/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    
    # Корзина и покупки
    path('cart/', views.cart_view, name='cart'),
    path('add-to-cart/<int:offer_id>/', views.add_to_cart, name='add_to_cart'),
    path('add-platform-to-cart/<int:product_id>/', views.add_platform_to_cart, name='add_platform_to_cart'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/confirm/', views.checkout_confirm, name='checkout_confirm'),
    path('purchase-history/', views.purchase_history, name='purchase_history'),
    path('receipt/<int:pk>/', views.receipt_detail, name='receipt_detail'),
    
    # Управление товарами (для менеджеров)
    path('product/new/', views.ProductCreateView.as_view(), name='product_create'),
    path('product/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product_update'),
    path('product/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),
    path('offer/new/<int:product>/', views.OfferCreateView.as_view(), name='offer_create'),
    path('offer/<int:pk>/edit/', views.OfferUpdateView.as_view(), name='offer_update'),
    
    # Автоматический поиск предложений
    path('search-market-offers/<int:product_id>/', views.search_market_offers, name='search_market_offers'),
    path('create-offer-from-search/<int:product_id>/', views.create_offer_from_search, name='create_offer_from_search'),
    
    # Аутентификация
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', views.register, name='register'),
] 