from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import AnonymousUser

#------------------- Auth -------------------

class LoginAuth(LoginRequiredMixin):
    
    def dispatch(self, request, *args, **kwargs):
        # First check if the user is authenticated
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        
        # Check if the user is an instance of AnonymousUser (this is redundant if we already check is_authenticated)
        if isinstance(request.user, AnonymousUser):
            raise PermissionDenied("You do not have permission to access this page.")
        
        # Check if the user has a 'company' attribute or a role
        if  not hasattr(request.user, 'role'):
            raise PermissionDenied("You must be associated with a company to access this page.")
        return super().dispatch(request, *args, **kwargs)
        
    
#------------------- Company ----------------


class LoginAdmin(LoginRequiredMixin):
    
    def dispatch(self, request, *args, **kwargs):
        # First check if the user is authenticated
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        
        user_role = request.user.role

        # Check if the user is an instance of AnonymousUser (this is redundant if we already check is_authenticated)
        if isinstance(request.user, AnonymousUser):
            raise PermissionDenied("You do not have permission to access this page.")

        # Check if the user has a 'company' attribute or a role
        if  not hasattr(request.user, 'role'):
            raise PermissionDenied("You must be associated with a company to access this page.")

        # Check if the user has the correct role
        if user_role != 'admin':
            raise PermissionDenied("You must have the 'company' role to access this page.")
        
        return super().dispatch(request, *args, **kwargs)

#-------------------- User --------------------

class LoginStaff(LoginRequiredMixin):
    
    def dispatch(self, request, *args, **kwargs):
        user_role = request.user.role
        
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        
        # Check if the user is an instance of AnonymousUser (this is redundant if we already check is_authenticated)
        if isinstance(request.user, AnonymousUser):
            raise PermissionDenied("You do not have permission to access this page.")
        
        elif not hasattr(request.user, 'role'):
            raise PermissionDenied("You must be associated with a company to access this page.")
        
        elif user_role != 'staff':
            raise PermissionDenied("You do not have permission to access this page.")
        
        return super().dispatch(request, *args, **kwargs)


# Check if the user has a 'company' attribute (indicating association with a company)
#        if not getattr(request.user, 'company', None):
#           # Redirect to the company registration page if the user is not associated with a company
#           return redirect(reverse('company-registration'))