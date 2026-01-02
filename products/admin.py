from django.contrib import admin
from .models import Category, Product, Review, Order
from .models import Sale

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id","name","slug")

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id","name","price","category","available","pieces_available","created_at", "sizes", "description")
    list_filter = ("category","available","gender")
    search_fields = ("name","description")

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id","product","user","rating","created_at")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id","reference","user","amount","status", "confirm_status", "created_at")
    readonly_fields = ("metadata",)

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "profit_or_loss", "profit_or_loss_label", "date_paid")
    list_filter = ("is_profit", "date_paid")
    search_fields = ("customer_name",)

    def profit_or_loss_label(self, obj):
        return "Profit" if obj.is_profit else "Loss"
    profit_or_loss_label.short_description = "Profit / Loss"

