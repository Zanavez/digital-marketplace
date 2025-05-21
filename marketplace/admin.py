from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Product, Offer, Market, Cart, Receipt, FakeOffer

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser', 'groups')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Персональная информация', {'fields': ('first_name', 'last_name', 'middle_name', 'email', 'phone_number')}),
        ('Права доступа', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'is_superuser', 'is_staff'),
        }),
    )
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)

    def save_model(self, request, obj, form, change):
        if obj.is_superuser:
            obj.role = 'admin'
        super().save_model(request, obj, form, change)

class OfferInline(admin.TabularInline):
    model = Offer
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'popularity', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at', 'updated_at')
    inlines = [OfferInline]

@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'url', 'description', 'created_at', 'updated_at')
    search_fields = ('name', 'url', 'description')
    list_filter = ('created_at', 'updated_at')

@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('product', 'market', 'price', 'created_at', 'updated_at')
    list_filter = ('market', 'created_at', 'updated_at')
    search_fields = ('product__name', 'market__name')

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'offer', 'quantity', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'offer__product__name')

@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('user', 'offer', 'quantity', 'total_price', 'purchase_date')
    list_filter = ('purchase_date',)
    search_fields = ('user__username', 'offer__product__name')

@admin.register(FakeOffer)
class FakeOfferAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'market', 'price', 'title', 'url', 'created_at', 'updated_at')
    search_fields = ('product__name', 'market__name', 'title', 'url')
    list_filter = ('market', 'created_at', 'updated_at')

admin.site.register(User, CustomUserAdmin)
