from rest_framework.permissions import BasePermission

class IsAdminOrReadOnly(BasePermission):
    """
    Allow safe methods for everyone, but creation/updating/deletion only for admin (superuser).
    """
    def has_permission(self, request, view):
        if request.method in ('GET','HEAD','OPTIONS'):
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)

class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser: return True
        return obj.user == request.user
