# import os
# import uuid
# import requests
from multiprocessing import context
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, generics, filters, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, Product, Review, Order
from .serializers import CategorySerializer, ProductSerializer, ProductCreateUpdateSerializer, ReviewSerializer, OrderSerializer
from .permissions import IsAdminOrReadOnly, IsOwnerOrAdmin
from django.conf import settings
from rest_framework.parsers import MultiPartParser, FormParser 

from .models import Sale
from .serializers import SaleSerializer

# Payments
from django.core.mail import send_mail

from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator

import uuid
from decimal import Decimal
from django.utils import timezone
from .utils import send_transaction_emails

from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from datetime import datetime
from django.utils import timezone
from django.core.cache import cache




# Categories
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]

    def list(self, request, *args, **kwargs):
        cache_key = "categories:list"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        qs = self.queryset
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
        else:
            serializer = self.get_serializer(qs, many=True)
            response = Response(serializer.data)

        cache.set(cache_key, response.data, 30)
        return response

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)

        # ✅ Clear category list cache
        cache.delete("categories:list")

        # ✅ Clear any product list caches related to this category
        cache.delete_pattern(f"products:list:cat={instance.slug}:*")
        cache.delete_pattern("products:*")  # fallback for any other product lists

        return Response(status=status.HTTP_204_NO_CONTENT)




# Products
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name","description"]

    def create(self, request, *args, **kwargs):
        print(">>> DEBUG: Authenticated user:", request.user)
        print(">>> DEBUG: Is superuser:", request.user.is_superuser)
        print(">>> DEBUG: Is staff:", request.user.is_staff)
        print(">>> DEBUG: Authenticated:", request.user.is_authenticated)

        # ✅ Ensure only admin/staff can post
        if not request.user.is_staff and not request.user.is_superuser:
            return Response(
                {"detail": "You must be an admin to post a product."},
                status=status.HTTP_403_FORBIDDEN
            )

        # ✅ Automatically mark as available and active when created

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(available=True, is_active=True)

        cache.delete_pattern("products:*")

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data.copy()

        # ✅ Keep availability & active status unless explicitly changed
        if "available" not in data:
            data["available"] = instance.available
        if "is_active" not in data:
            data["is_active"] = instance.is_active

        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        cache.delete(f"product:{instance.id}")
        cache.delete_pattern("products:*")

        return Response(serializer.data, status=status.HTTP_200_OK)


    def get_serializer_class(self):
        if self.action in ["create","update","partial_update"]:
            return ProductCreateUpdateSerializer
        return ProductSerializer

    

    def list(self, request, *args, **kwargs):
        category = request.query_params.get("category")
        search = request.query_params.get("search")
        page_num = request.query_params.get("page", 1)

        cache_key = f"products:list:cat={category}:search={search}:page={page_num}"

        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        qs = self.queryset
        if category:
            qs = qs.filter(category__slug=category)
        if search:
            qs = qs.filter(name__icontains=search)

        page = self.paginate_queryset(qs)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
        else:
            serializer = self.get_serializer(qs, many=True)
            response = Response(serializer.data)

        cache.set(cache_key, response.data, 60 * 5)
        return response
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()  # get the product being deleted
        self.perform_destroy(instance)  # actually delete it from the database

        # Clear caches
        cache.delete(f"product:{instance.id}")      # delete individual product cache
        cache.delete_pattern("products:*")          # delete any product list caches

        return Response(status=status.HTTP_204_NO_CONTENT)





    @action(detail=True, methods=["get"], permission_classes=[permissions.AllowAny])
    def related(self, request, pk=None):
        cache_key = f"product:related:{pk}"

        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        p = self.get_object()
        qs = Product.objects.filter(category=p.category).exclude(pk=p.pk)[:10]
        data = ProductSerializer(qs, many=True).data

        cache.set(cache_key, data, 60 * 10)
        return Response(data)


    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def reviews(self, request, pk=None):
        product = self.get_object()
        if Review.objects.filter(product=product, user=request.user).exists():
            return Response({"detail":"You already reviewed this product"}, status=status.HTTP_400_BAD_REQUEST)
        rating = int(request.data.get("rating",0))
        comment = request.data.get("comment","")
        review = Review.objects.create(product=product, user=request.user, rating=rating, comment=comment)
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)
    

    def retrieve(self, request, *args, **kwargs):
        pk = kwargs["pk"]
        cache_key = f"product:detail:{pk}"

        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        response = super().retrieve(request, *args, **kwargs)

        cache.set(cache_key, response.data, 60 * 10)
        return response


# List reviews for a product
class ProductReviewsView(generics.ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.AllowAny]
    def get_queryset(self):
        pid = self.kwargs.get("product_id")
        return Review.objects.filter(product_id=pid)
    
    
class AllReviewsView(generics.ListAPIView):
    queryset = Review.objects.all().order_by("-created_at")
    serializer_class = ReviewSerializer
    permission_classes = [permissions.AllowAny]


# Orders listing
class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Order.objects.all().order_by("-created_at")
        return Order.objects.filter(user=user).order_by("-created_at")


# Create an order (called from Cart -> AccountDetails flow)
class OrderCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        amount = request.data.get("amount")
        metadata = request.data.get("metadata", {})

        if not amount:
            return Response({"error": "amount is required"}, status=status.HTTP_400_BAD_REQUEST)

        # generate short unique reference
        reference = str(uuid.uuid4()).replace("-", "")[:12]

        # ensure amount decimal
        try:
            amount_val = Decimal(amount)
        except Exception:
            return Response({"error": "invalid amount"}, status=status.HTTP_400_BAD_REQUEST)

        order = Order.objects.create(
            user=user,
            reference=reference,
            amount=amount_val,
            status="initiated",       # created but not paid
            confirm_status="pending",
            metadata=metadata or {}
        )

        # respond with serialized order
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# Mark order as "user has made payment" — user clicks "I Have Made Payment"
class OrderMarkPaidView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        order = get_object_or_404(Order, pk=pk)

        # ensure only owner (or admin) can mark the order as paid
        if order.user != user and not user.is_superuser:
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)

        # set a simple flag inside metadata to mark user payment attempt
        meta = order.metadata or {}
        meta["user_marked_paid"] = True
        meta["user_marked_paid_at"] = timezone.now().isoformat()
        order.metadata = meta
        order.save(update_fields=["metadata"])

        # Send notification to admin (use your existing util)
        try:
            product_names = ", ".join([i.get("name", "") for i in meta.get("items", [])]) if meta.get("items") else "Product(s)"
            context = {
                "customer_name": order.user.username,
                "product_names": product_names,
                "amount": str(order.amount),
                "reference": order.reference,
            }
            admin_email = getattr(settings, "ADMIN_EMAIL", settings.DEFAULT_FROM_EMAIL)
            send_transaction_emails(admin_email, order.user.email, context)
        except Exception as e:
            print(f"Error sending notify email to admin: {e}")

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)


# Retrieve single order for AccountDetails page (owner or admin)
class OrderDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderSerializer
    queryset = Order.objects.all()

    def get_object(self):
        obj = get_object_or_404(Order, pk=self.kwargs.get("pk"))
        # only owner or admin can view
        if self.request.user != obj.user and not self.request.user.is_superuser:
            raise permissions.PermissionDenied("Not allowed")
        return obj




class ConfirmPaymentView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)

        # Update confirmation details
        order.status = "paid"
        order.confirmed = True
        order.confirm_status = "confirmed"
        order.save()

        # ✅ Send styled confirmation email
        logo_url = f"{settings.SITE_URL}/static/images/heromefab.jpg"
        
        year = datetime.now().year

        html_content = render_to_string("email_template.html", {
            "logo_url": logo_url,
            "year": year,
            "body_content": f"""
                <h2>Payment Confirmed</h2>
                <p>Hi {order.user.username},</p>
                <p>Your payment of ₦{order.amount}  has been confirmed. Please login and check your Transaction for confirmation.</p>
                <p>Your order is now being processed. Thank you for shopping with <span class="highlight">Herome_Fab</span>!</p>
                <p><b>Transaction Reference:</b> {order.reference}</p>
            """
        })
        text_content = strip_tags(html_content)

        msg = EmailMultiAlternatives(
            subject=f"Payment Confirmed - Reference {order.reference}",
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[order.user.email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)

        # ✅ Return updated order data to frontend
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class ReversePaymentView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)

        # Only reverse if it's already confirmed
        if order.confirm_status != "confirmed":
            return Response({"detail": "Order is not confirmed yet."}, status=status.HTTP_400_BAD_REQUEST)

        order.status = "pending"
        order.confirmed = False
        order.confirm_status = "pending"
        order.save()

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)



class SaleListCreateView(generics.ListCreateAPIView):
    queryset = Sale.objects.all().order_by('-id')
    serializer_class = SaleSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class SaleRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    permission_classes = [permissions.IsAdminUser]





