from rest_framework import serializers
from django.db.models import Avg
from .models import Category, Product, Review, Order
from django.conf import settings
from userapp.serializers import UserSerializer

from .models import Sale

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id","name","slug")

class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Review
        fields = ("id","user","rating","comment","created_at")

        

class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    avg_rating = serializers.SerializerMethodField()
    reviews = ReviewSerializer(many=True, read_only=True)
    class Meta:
        model = Product
        fields = ("id","name","slug","description","price","available","category","gender","color","pieces_available","size_guide","sizes","image1","image2","avg_rating","reviews")

    def get_avg_rating(self,obj):
        return obj.reviews.aggregate(avg=Avg("rating"))["avg"] or 0

class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"

class OrderSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    class Meta:
        model = Order
        fields = ("id","user","reference","amount","status", "confirm_status", "metadata","created_at")

    def get_user(self, obj):
        user = obj.user
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "phone_number": getattr(user, "phone_number", None) 
        }




class SaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = '__all__'
        read_only_fields = ['created_by', 'profit_or_loss', 'is_profit']

