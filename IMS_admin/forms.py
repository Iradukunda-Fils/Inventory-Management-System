from django import forms
from IMS_production.models import Product, Category
from phonenumber_field.formfields import PhoneNumberField

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'name', 'price', 'quantity', ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customize the 'category' field to show options from the Category table
        category = Category.objects.all()
        self.fields['category'].queryset = category
        self.fields['category'].label_from_instance = lambda obj: f"{obj.name}"
        self.fields['category'].widget.attrs.update({'class': 'form-select'})  # Add Bootstrap styling



class SendSMSForm(forms.Form):
    SCHEDULE_CHOICES = [
        ("now", "Send Now"),
        ("interval", "Interval"),
        ("crontab", "Cron (Advanced)"),
    ]

    # -----------------------------
    # Core Fields
    # -----------------------------
    phone_number = PhoneNumberField(
        label="Recipient Phone Number",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "+250783071229",
            "aria-label": "Phone Number",
        }),
        help_text="Include country code. Example: +250783071229"
    )
    message = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "placeholder": "Type your SMS here...",
            "rows": 3,
        }),
        help_text="Max 160 characters for standard SMS"
    )
    sender = forms.CharField(
        label="Sender ID",
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Optional sender name (defaults to TWARA)"
        }),
        help_text="Optional: Defaults to 'TWARA' if empty"
    )

    # -----------------------------
    # Schedule Type
    # -----------------------------
    schedule_type = forms.ChoiceField(
        label="Schedule Type",
        choices=SCHEDULE_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        initial="now",
        help_text="Choose when to send the message"
    )

    # -----------------------------
    # Interval Scheduling Fields
    # -----------------------------
    every = forms.IntegerField(
        label="Repeat Every",
        required=False,
        initial=1,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "min": "1",
        }),
        help_text="Repeat every N minutes/hours/days/weeks"
    )
    period = forms.ChoiceField(
        label="Interval Period",
        required=False,
        choices=[("minutes", "Minutes"), ("hours", "Hours"), ("days", "Days"), ("weeks", "Weeks")],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    # -----------------------------
    # Cron Scheduling Fields
    # -----------------------------
    minute = forms.CharField(
        label="Minute",
        required=False,
        initial="*",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "*"}),
        help_text="0-59 or * for every minute"
    )
    hour = forms.CharField(
        label="Hour",
        required=False,
        initial="*",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "*"}),
        help_text="0-23 or * for every hour"
    )
    day_of_week = forms.CharField(
        label="Day of Week",
        required=False,
        initial="*",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "*"}),
        help_text="0-6 (0=Sunday) or * for every day"
    )
    day_of_month = forms.CharField(
        label="Day of Month",
        required=False,
        initial="*",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "*"}),
        help_text="1-31 or * for every day"
    )
    month_of_year = forms.CharField(
        label="Month",
        required=False,
        initial="*",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "*"}),
        help_text="1-12 or * for every month"
    )
