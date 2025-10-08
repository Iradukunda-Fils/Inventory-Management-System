from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

class UserCreationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'}),
        label="Password"
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}),
        label="Confirm Password"
    )

    class Meta:
        model = get_user_model()  # Points to your custom user model
        fields = ['username', 'email', "phone_number", 'role']
        widgets = {
            'role': forms.Select(attrs={'class': 'select'}),
            'username': forms.TextInput(attrs={'placeholder': 'Username'}),
            'email': forms.TextInput(attrs={'placeholder': 'Email'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        # Check if passwords match
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Passwords do not match.")

        # Validate password strength
        if password:
            try:
                validate_password(password)
            except ValidationError as e:
                self.add_error('password', e)
                
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        # Set the hashed password
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user
    
# Custom form to handle username, email, and role
class UserUpdateForm(forms.ModelForm):
    
    password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'placeholder': 'New Password','name': 'update', 'id': 'update'}))
    password_confirm = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'placeholder': 'Confirm New Password', 'name': 'update', 'id': 'update'}))
    class Meta:
        model = get_user_model()
        fields = ['username', 'role', 'email', "phone_number"]
        widgets = {
            'role': forms.Select(attrs={'class': 'select'}),
            }
        
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password != password_confirm:
            self.add_error('password_confirm', "Passwords do not match.")
        return cleaned_data















