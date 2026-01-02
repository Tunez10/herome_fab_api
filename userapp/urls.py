from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterView, UserProfileView, UserListView, CreateUserByStaffView, CustomTokenObtainPairView, AdminDeleteUserView, VerifyCodeView
from .views import PasswordResetRequestView, PasswordResetConfirmView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("profile/", UserProfileView.as_view(), name="user_profile"),
    path("all-users/", UserListView.as_view(), name="all_users"),
    path("create-user-by-staff/", CreateUserByStaffView.as_view(), name="create_user_by_staff"),
    path("users/<int:pk>/delete/", AdminDeleteUserView.as_view(), name="admin_delete_user"),
    path("verify/", VerifyCodeView.as_view(), name="verify_account"), 
    path("forgot-password/", PasswordResetRequestView.as_view()),
    path("reset-password/<uidb64>/<token>/", PasswordResetConfirmView.as_view()),
]
