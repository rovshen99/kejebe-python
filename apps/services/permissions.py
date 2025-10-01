from rest_framework.permissions import BasePermission, SAFE_METHODS

from apps.users.models import RoleEnum


class IsVendor(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == RoleEnum.VENDOR)


class IsServiceVendorOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return bool(request.user and getattr(obj, 'vendor_id', None) == request.user.id)


class IsServiceProductVendorOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        service = getattr(obj, 'service', None)
        vendor_id = getattr(service, 'vendor_id', None) if service else None
        return bool(request.user and vendor_id == request.user.id)

