from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.mail import send_mail
from django.conf import settings
from .models import CustomUser


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "username", "email", "phone_number", "profile_picture", "is_staff", "is_superuser"]
        read_only_fields = ["is_staff", "is_superuser"]

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = CustomUser
        fields = ["id", "username", "email", "phone_number", "profile_picture", "password"]

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
            phone_number=validated_data.get("phone_number", "")
        )

        pic = validated_data.get("profile_picture")
        if pic:
            user.profile_picture = pic
            user.save()

        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["email"] = user.email
        token["is_staff"] = user.is_staff
        token["is_superuser"] = user.is_superuser
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # ❗ Prevent login if user is not verified
        if not self.user.is_verified:
            raise serializers.ValidationError(
                {"detail": "Account not verified. Please check your email for the verification code."}
            )

        data["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email,
            "is_staff": self.user.is_staff,
            "is_superuser": self.user.is_superuser,
            "phone_number": self.user.phone_number,
            "profile_picture": self.user.profile_picture.url if self.user.profile_picture else None
        }
        return data
