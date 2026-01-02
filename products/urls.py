from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AllReviewsView, CategoryViewSet, OrderDetailView, OrderMarkPaidView, ProductViewSet, ProductReviewsView, OrderListView, ReversePaymentView
from .views import SaleListCreateView, SaleRetrieveUpdateDestroyView, OrderCreateView, ConfirmPaymentView


router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("products", ProductViewSet, basename="product")

urlpatterns = [
    path("", include(router.urls)),
    path("products/<int:product_id>/reviews-list/", ProductReviewsView.as_view(), name="product-reviews"),
    path("orders/", OrderListView.as_view(), name="orders"),
    path("orders/create/", OrderCreateView.as_view(), name="order-create"),
    path("orders/<int:pk>/", OrderDetailView.as_view(), name="order-detail"),
    path("orders/<int:pk>/mark-paid/", OrderMarkPaidView.as_view(), name="order-mark-paid"),
    path("sales/", SaleListCreateView.as_view(), name="sales"),
    path("sales/<int:pk>/", SaleRetrieveUpdateDestroyView.as_view(), name="sale-detail"),
    path("orders/<int:pk>/confirm-payment/", ConfirmPaymentView.as_view(), name="confirm-payment"),
    path("reviews/all/", AllReviewsView.as_view(), name="all-reviews"),
    path("orders/<int:pk>/reverse-payment/", ReversePaymentView.as_view(), name="reverse-payment"),

   
]
