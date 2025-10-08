from django.shortcuts import render,redirect
from django.views.generic.edit import CreateView
from django.contrib.auth.views import LoginView
from django.views.generic.edit import UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.views import View
from django.views.generic import DeleteView
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import logout
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from sms_tasks.tasks import send_sms

from permission.login import LoginAdmin, LoginAuth
from .forms import UserUpdateForm
from .forms import UserCreationForm
import uuid

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

class RegistrationView(LoginAdmin, CreateView):
    form_class = UserCreationForm
    template_name = 'authentication/registration.html'
    success_url = reverse_lazy('list-users')

    def form_valid(self, form):
        # Save the new user first
        response = super().form_valid(form)
        user = self.object

        # Send notifications
        self.send_notifications(user)

        return response

    # ------------------------------
    # Notification handling
    # ------------------------------
    def send_notifications(self, user):
        recipient = user.email
        user_name = user.username
        site_name = get_current_site(self.request).name
        login_url = self.request.build_absolute_uri(reverse_lazy('login'))
        
        # Ensure phone number is a string (avoid serialization issues)
        phone_number = str(user.phone_number) if user.phone_number else None

        # --- SMS ---
        if phone_number:
            message = f"""
            Ref: {uuid.uuid4().hex[:6]}  
            Hello, {user_name}!
            Welcome to our inventory management system.

            You can click this link to login:
            {login_url}

            Thank you.
            Regards,
            IMS Team
            """
            send_sms.delay(phone_number, message)
        

        # # --- Email ---
        # email_service = EmailService()
        
        # task_id = email_service.send_welcome_email(
        #     recipient=recipient,
        #     user_name=user_name,
        #     site_name=site_name,
        #     login_url=login_url,
        # )
        


        

#--------------------------------------------------------------------<> Update View <>-----------------------------------------------#

class UserUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'authentication/user/user-update.html'
    success_url = reverse_lazy('list-users')

    # IMPORTANT: tell UpdateView to use 'username' from the URL
    slug_field = 'username'      # the field in your User model
    slug_url_kwarg = 'user'      # the URL kwarg from your path()

    login_url = reverse_lazy('login')

    def test_func(self):
        return self.request.user.is_admin

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if not self.request.user.is_admin:
            form.fields.pop('role', None)
        return form

    def form_valid(self, form):
        user_instance = form.save(commit=False)
        password = form.cleaned_data.get('password')
        password_confirm = form.cleaned_data.get('password_confirm')

        if password:
            if password != password_confirm:
                form.add_error('password_confirm', "Passwords do not match.")
                return self.form_invalid(form)
            validate_password(password, user_instance)
            user_instance.set_password(password)

        # Phone number safely
        phone_number_obj = form.cleaned_data.get('phone_number')
        user_instance.phone_number = str(phone_number_obj) if phone_number_obj else None

        user_instance.save()

        self.send_notifications(user_instance)

        if self.request.user == user_instance and password:
            update_session_auth_hash(self.request, user_instance)
            messages.success(self.request, "Your credentials have been updated successfully!")
        else:
            messages.success(self.request, f"User {user_instance.username} has been updated successfully!")

        return super().form_valid(form)

    def send_notifications(self, user_instance):

        # SMS notification via Celery
        if user_instance.phone_number:
            message = f"""
            Hello, {user_instance.username}!
            Your account has been updated successfully!

            You can click this link for updates:
            {self.request.build_absolute_uri()}

            Regards, IMS Team
            """
            send_sms.delay(str(user_instance.phone_number), message)
        
        # # Email notification
        # email_service = EmailService()
        
        # email_service.send_notification_email(
        #     recipient=getattr(settings, "DEFAULT_FROM_EMAIL"),
        #     title="Credentials Updated Successfully",
        #     message=f"User {user_instance.username} has updated their credentials.",
        #     action_url=self.request.build_absolute_uri(),
        #     action_text="View User"
        # )


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




