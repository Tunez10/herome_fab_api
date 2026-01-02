from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import CustomUser
from .serializers import UserSerializer, RegisterSerializer, CustomTokenObtainPairSerializer

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from datetime import datetime
from django.conf import settings
import random

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from rest_framework.permissions import AllowAny

token_generator = PasswordResetTokenGenerator()


# Temporary store for unverified registrations
PENDING_REGISTRATIONS = {}

# Register endpoint (open)
class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            username = serializer.validated_data["username"]
            password = serializer.validated_data["password"]

            # prevent duplicate registrations
            if CustomUser.objects.filter(email=email).exists():
                return Response({"detail": "Email already registered."}, status=status.HTTP_400_BAD_REQUEST)

            # Generate verification code
            verification_code = random.randint(100000, 999999)

            # Store temporarily in memory (not in DB yet)
            PENDING_REGISTRATIONS[email] = {
                "username": username,
                "password": password,
                "verification_code": verification_code,
            }

            year = datetime.now().year
            logo_url = f"{settings.SITE_URL}/static/images/heromefab.jpg"

            # ✨ Styled email
            html_content = render_to_string("email_template.html", {
                "logo_url": logo_url,
                "year": year,
                "body_content": f"""
                    <h2 style="color:#ff6600; text-align:center;">Welcome to Herome_Fab!</h2>
                    <p>Hi <b>{username}</b>,</p>
                    <p>Thank you for joining <span class="highlight">Herome_Fab</span> — Nigeria’s leading fashion community.</p>
                    <p>To complete your registration, please use the verification code below:</p>

                    <div style="
                        text-align:center;
                        margin:30px 0;
                        background:#fff3e6;
                        border-radius:10px;
                        padding:20px;
                        display:inline-block;
                        box-shadow:0 0 15px rgba(255,102,0,0.2);
                    ">
                        <h1 style="
                            color:#ff6600;
                            font-size:36px;
                            letter-spacing:8px;
                            margin:0;
                            font-weight:700;
                        ">
                            {verification_code}
                        </h1>
                        <p style="margin-top:8px; color:#555;">(Enter this code in the verification page)</p>
                    </div>

                    <p>Once verified, you can log in and start shopping for amazing fashion products.</p>
                    <p style="margin-top:25px;">Cheers,<br><b>Herome_Fab</b></p>
                """
            })

            text_content = strip_tags(html_content)

            subject = "Verify Your Herome_Fab Account"
            from_email = "Herome_Fab <no-reply@heromefab.com>"
            to = [email]

            msg = EmailMultiAlternatives(subject, text_content, from_email, to)
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            return Response({"detail": "Verification code sent to your email."}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Verify user email with code
class VerifyCodeView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        code = request.data.get("code")

        if not email or not code:
            return Response(
                {"detail": "Email and verification code are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pending = PENDING_REGISTRATIONS.get(email)
        if not pending:
            return Response({"detail": "No pending registration found for this email."},
                            status=status.HTTP_404_NOT_FOUND)

        if str(pending["verification_code"]) == str(code):
            # ✅ Create the user now
            user = CustomUser.objects.create_user(
                username=pending["username"],
                email=email,
                password=pending["password"],
                is_verified=True
            )
            user.save()

            # remove from temporary store
            del PENDING_REGISTRATIONS[email]

            return Response({"detail": "Account verified and created successfully."}, status=status.HTTP_201_CREATED)

        return Response({"detail": "Invalid verification code."}, status=status.HTTP_400_BAD_REQUEST)


# Profile (logged in)
class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        return self.update_profile(request, partial=False)

    def patch(self, request):
        return self.update_profile(request, partial=True)

    def update_profile(self, request, partial):
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=partial)

        if serializer.is_valid():
            new_password = request.data.get("password")
            if new_password:
                user.set_password(new_password)

            serializer.save()
            if new_password:
                user.save()
                return Response({"success": True, "message": "Password updated successfully. Please log in again."})

            return Response({"success": True, "message": "Profile updated successfully.", "data": serializer.data})
        return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        user = request.user
        user.delete()
        return Response({"detail": "Account deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


# Admin: list all users
class UserListView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]


# Admin delete
class AdminDeleteUserView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def delete(self, request, pk):
        try:
            user = CustomUser.objects.get(pk=pk)
            if request.user.id == user.id:
                return Response({"detail": "You cannot delete your own account."}, status=status.HTTP_400_BAD_REQUEST)
            if user.is_superuser:
                return Response({"detail": "Cannot delete another superuser."}, status=status.HTTP_403_FORBIDDEN)
            user.delete()
            return Response({"detail": "User deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except CustomUser.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)


# Staff create
class CreateUserByStaffView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)
        return super().post(request, *args, **kwargs)


# Login
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer





class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response({"detail": "Email is required"}, status=400)

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({"detail": "Email not found"}, status=404)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)

        reset_link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}"

        year = datetime.now().year
        logo_url = f"{settings.SITE_URL}/static/images/heromefab.jpg"

        html_content = render_to_string("email_template.html", {
            "logo_url": logo_url,
            "year": year,
            "body_content": f"""
                <h2>Password Reset</h2>
                <p>Hello <b>{user.username}</b>,</p>
                <p>You requested to reset your password. Below is the password reset link</p>
                <p>
                    <a href="{reset_link}"
                       style="display:inline-block;padding:12px 20px;
                       background:#ff6600;color:#fff;border-radius:6px;
                       text-decoration:none;">
                       Reset Password Link
                    </a>
                </p>
                <p>If you didn’t request this, ignore this email.</p>
            """
        })

        msg = EmailMultiAlternatives(
            "Reset Your Password",
            strip_tags(html_content),
            settings.DEFAULT_FROM_EMAIL,
            [email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        return Response({"detail": "Password reset link sent"}, status=200)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)
        except Exception:
            return Response({"detail": "Invalid reset link"}, status=400)

        if not token_generator.check_token(user, token):
            return Response({"detail": "Invalid or expired token"}, status=400)

        return Response({"email": user.email}, status=200)

    def post(self, request, uidb64, token):
        password = request.data.get("password")

        if not password:
            return Response({"detail": "Password is required"}, status=400)

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)
        except Exception:
            return Response({"detail": "Invalid reset link"}, status=400)

        if not token_generator.check_token(user, token):
            return Response({"detail": "Invalid or expired token"}, status=400)

        user.set_password(password)
        user.save()

        return Response({"detail": "Password reset successful"}, status=200)


