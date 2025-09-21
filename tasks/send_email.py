from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.core.mail import send_mail
from celery import shared_task
from django.conf import settings


class SendEmailTask:
    
    def __init__(self, to_email, subject, template_name, context, from_email=getattr(settings, EMAIL_HOST_PASSWORD)):
        self.to_email = to_email.split(",") if isinstance(to_email, str) else to_email
        self.subject = subject
        self.template_name = template_name
        self.context = context
        self.from_email = from_email
        self.html_message = render_to_string(self.template_name, self.context)
    
    @shared_task(bind=True, max_retries=3)
    def send_template_email(self):
        email = EmailMessage(
            self.subject,
            self.html_message,
            self.from_email,
            self.to_email,
        )
        email.content_subtype = "html"
        try:
            email.send()
        except Exception as e:
            raise self.retry(exc=exc, countdown=60)
        
    @shared_task(bind=True, max_retries=3)
    def send(self):
        try:
            send_mail(
                "Welcome!",
                "Thanks for registering.",
                "your_email@gmail.com",
                [to_email],
                fail_silently=False,
            )
        except Exception as exc:
            raise self.retry(exc=exc, countdown=60)  # retry after 1 min

def send_template_email(user):
    subject = "Account Activation"
    html_message = render_to_string("emails/activation.html", {"user": user})

    email = EmailMessage(
        subject,
        html_message,
        "your_email@gmail.com",
        [user.email],
    )
    email.content_subtype = "html"
    email.send()
    

def send_email_task(self, to_email):
    pass


@shared_task(bind=True, max_retries=3)
def send_welcome_email(to_email):
    try:
        send_mail(
            "Welcome!",
            "Thanks for registering.",
            "your_email@gmail.com",
            [to_email],
            fail_silently=False,
        )
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)  # retry after 1 min

