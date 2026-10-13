from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts import roles


class RolePermission(BasePermission):
    """Role-based access driven by attributes on the view.

    * ``read_roles``   - GET / HEAD / OPTIONS
    * ``write_roles``  - POST / PUT / PATCH
    * ``delete_roles`` - DELETE
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            allowed = view.read_roles
        elif request.method == "DELETE":
            allowed = view.delete_roles
        else:
            allowed = view.write_roles
        return user.role in allowed


class IsClinicStaff(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in roles.STAFF)
