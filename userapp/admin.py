from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Extra", {"fields": ("phone_number","profile_picture")}),
    )
    list_display = ("username","email","is_staff","is_superuser", "phone_number")
