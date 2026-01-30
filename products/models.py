from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from .utils import generate_unique_slug

from django.contrib.auth import get_user_model

User = settings.AUTH_USER_MODEL

GENDER_CHOICES = (
    ("male", "Male"),
    ("female", "Female"),
    ("unisex", "Unisex"),
    ("kids", "Kids"),
)

class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self): return self.name

# models.py
class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    available = models.BooleanField(default=True)
    category = models.ForeignKey(Category, related_name="products", on_delete=models.SET_NULL, null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default="unisex")
    color = models.CharField(max_length=50, blank=True)
    pieces_available = models.PositiveIntegerField(default=1)
    size_guide = models.TextField(blank=True)
    sizes = ArrayField(models.CharField(max_length=10), default=list, blank=True)
    
    image1 = models.ImageField(null=True, blank=True)
    image2 = models.ImageField(null=True, blank=True)

    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Product, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Review(models.Model):
    product = models.ForeignKey(Product, related_name="reviews", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="reviews", on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("product","user")
        ordering = ("-created_at",)

    def __str__(self): return f"{self.user} - {self.product} - {self.rating}"

class Order(models.Model):
    STATUS_CHOICES = (("initiated","Initiated"),("paid","Paid"),("failed","Failed"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="orders", on_delete=models.CASCADE)
    reference = models.CharField(max_length=200, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="initiated")

    confirm_status = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("confirmed", "Confirmed")],
        default="pending"
    )
    metadata = models.JSONField(default=dict)  # snapshot of items
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"Order {self.reference} by {self.user}"


# productapp/models.py (or salesapp/models.py)


User = get_user_model()

class Sale(models.Model):
    customer_name = models.CharField(max_length=100)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    cost_of_production = models.DecimalField(max_digits=10, decimal_places=2)
    workmanship = models.DecimalField(max_digits=10, decimal_places=2)
    date_paid = models.DateField()
    date_completed = models.DateField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    profit_or_loss = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_profit = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        total_cost = self.cost_of_production + self.workmanship
        difference = self.amount_paid - total_cost
        self.profit_or_loss = difference
        self.is_profit = difference >= 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer_name} - {'Profit' if self.is_profit else 'Loss'}"

