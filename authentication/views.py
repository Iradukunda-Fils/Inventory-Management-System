from django.shortcuts import render,redirect
from django.views.generic.edit import CreateView
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.views import View
from django.views.generic import DeleteView
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import logout
from django.contrib.auth.mixins import UserPassesTestMixin


from permission.login import LoginAdmin, LoginAuth
from .forms import UserUpdateForm
from .forms import UserCreationForm

User = get_user_model()

#--------------------------------------------------------------------<> Create View <>-----------------------------------------------#


def logout(request):
    return render(request,'logout.html')

class AuthLoginView(LoginView):
    template_name = 'authentication/login.html'     

    def get_success_url(self):
        if self.request.user.role == 'admin':
            return reverse_lazy('admin-dashboard')
        elif self.request.user.role == 'staff':
            return reverse_lazy('staff-dashboard')
        else:
            # Add error message and redirect to a safe fallback URL
            messages.error(self.request, 'Permission denied.')
            return reverse_lazy('login')
    
    
class RegistrationView(LoginAdmin, CreateView):
    form_class = UserCreationForm  # Reference the form class, not an instance
    template_name = 'authentication/registration.html'
    success_url = reverse_lazy('list-users')
    
#--------------------------------------------------------------------<> Update View <>-----------------------------------------------#

class UserUpdateView(UserPassesTestMixin, LoginAdmin, View):
    login_url = reverse_lazy('login')
    success_url = reverse_lazy('list-users')
    user_form = UserUpdateForm
    template_name = 'authentication/user/user-update.html'

    def get(self, request, user):
        user_instance = get_object_or_404(User, username=user)
        context = {
            'form': self.user_form(instance=user_instance),
        }
        return render(request, self.template_name, context)

    def post(self, request, user):
        user_instance = get_object_or_404(User, username=user)
        form = self.user_form(request.POST, instance=user_instance)

        if form.is_valid():
            # Get the new password and confirmation from the form
            new_password = form.cleaned_data.get('password')
            password_confirm = form.cleaned_data.get('password_confirm')

            # Check if passwords match
            if new_password and new_password == password_confirm:
                try:
                    # Validate the new password using Django's validators
                    validate_password(new_password, user_instance)
                    
                    # Set the new password
                    user_instance.set_password(new_password)
                except ValidationError as e:
                    form.add_error('password', e)
                    return render(request, self.template_name, {'form': form})

            # Update other fields
            user_instance.username = form.cleaned_data.get('username')
            user_instance.email = form.cleaned_data.get('email')
            user_instance.role = form.cleaned_data.get('role')  # Adjust if role exists
            
            user_instance.save()

            # If the logged-in user is updating their own password, keep them logged in
            if request.user == user_instance:
                update_session_auth_hash(request, user_instance)
                messages.success(request, "Your password and credentials have been updated successfully!")
                
            else:
                messages.success(request, f"The user {user_instance.username} has been updated successfully!")
            
            return redirect(self.success_url)
        else:
            messages.error(request, "Please correct the errors below.")
            
        return render(request, self.template_name, {'form': form})
    
    def test_func(self):
        return self.request.user.is_admin

#--------------------------------------------------------------------<> Delete View <>-----------------------------------------------#
    
class UserDeleteView(LoginAdmin, DeleteView):
    model = User
    template_name = 'authentication/user/user-delete.html'
    success_url = reverse_lazy('list-users')
    
    
#--------------------------------------------------------------------<> Delete View <>-----------------------------------------------#


class LogoutView(LoginAuth, View):
    login_url = reverse_lazy('login')
    tempelate_name = 'logout.html'
    success_url  = reverse_lazy('login')
    
    def get(self, request):
        return render(request,self.tempelate_name)
    
    def post(self, request):
        logout(request)
        messages.success(request, "You have been successfully logged out.")
        return redirect(self.success_url)




