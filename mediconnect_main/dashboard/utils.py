from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

def staff_required(view_func):
    @login_required
    def _wrapped(request, *args, **kwargs):
        u = request.user
        if getattr(u, 'is_superadmin', False) or getattr(u, 'is_admin', False) or getattr(u, 'is_staff', False):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("You don't have permission to access the dashboard.")
    return _wrapped
