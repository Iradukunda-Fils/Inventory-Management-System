from typing import Dict, Any, List, Optional, Union
from django.core.mail import EmailMultiAlternatives
from django.template import Context, Template
from django.conf import settings
from celery import shared_task
import logging

logger = logging.getLogger('email_service')


class EmailService:
    """
    Professional email service for handling different types of emails
    Supports synchronous and asynchronous sending via Celery
    """
    
    # Email type templates
    EMAIL_TEMPLATES = {
        'welcome': {
            'subject': 'Welcome to {{site_name}}, {{user_name}}!',
            'html': '''
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h1 style="color: #333;">Welcome {{user_name}}!</h1>
                    <p>Thank you for joining {{site_name}}. We're excited to have you on board.</p>
                    <p><a href="{{login_url}}" style="background: #007cba; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Get Started</a></p>
                </div>
            ''',
            'text': 'Welcome {{user_name}}! Thank you for joining {{site_name}}. Visit: {{login_url}}'
        },
        'password_reset': {
            'subject': 'Reset Your Password',
            'html': '''
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2>Password Reset Request</h2>
                    <p>Hi {{user_name}},</p>
                    <p>You requested a password reset. Click the link below to reset your password:</p>
                    <p><a href="{{reset_url}}" style="background: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p>
                    <p><small>This link expires in {{expires_in}} hours. If you didn't request this, please ignore this email.</small></p>
                </div>
            ''',
            'text': 'Hi {{user_name}}, reset your password: {{reset_url}} (expires in {{expires_in}} hours)'
        },
        'notification': {
            'subject': '{{title}}',
            'html': '''
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #333;">{{title}}</h2>
                    <p>{{message}}</p>
                    {% if action_url %}
                    <p><a href="{{action_url}}" style="background: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">{{action_text|default:"View Details"}}</a></p>
                    {% endif %}
                </div>
            ''',
            'text': '{{title}}: {{message}}{% if action_url %} - {{action_url}}{% endif %}'
        },
        'order_confirmation': {
            'subject': 'Order Confirmation #{{order_number}}',
            'html': '''
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2>Order Confirmed!</h2>
                    <p>Hi {{customer_name}},</p>
                    <p>Your order #{{order_number}} has been confirmed.</p>
                    <div style="background: #f8f9fa; padding: 15px; margin: 20px 0;">
                        <strong>Order Total: {{total_amount}}</strong>
                    </div>
                    <p>Estimated delivery: {{delivery_date}}</p>
                    <p><a href="{{tracking_url}}">Track Your Order</a></p>
                </div>
            ''',
            'text': 'Order #{{order_number}} confirmed for {{customer_name}}. Total: {{total_amount}}. Track: {{tracking_url}}'
        }
    }
    
    def __init__(self, from_email: str = None):
        """
        Initialize EmailService
        
        Args:
            from_email: Default sender email address
        """
        self.from_email = from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
    
    def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        """Render template with context"""
        if not template:
            return ""
        django_template = Template(template)
        return django_template.render(Context(context))
    
    def _prepare_email_content(self, email_type: str, context: Dict[str, Any]) -> Dict[str, str]:
        """Prepare email content from template"""
        if email_type not in self.EMAIL_TEMPLATES:
            raise ValueError(f"Unknown email type: {email_type}")
        
        template = self.EMAIL_TEMPLATES[email_type]
        
        return {
            'subject': self._render_template(template['subject'], context),
            'html_body': self._render_template(template['html'], context),
            'text_body': self._render_template(template['text'], context)
        }
    
    def send_email(self, 
                   recipient: Union[str, List[str]],
                   email_type: str = None,
                   subject: str = None,
                   html_body: str = None,
                   text_body: str = None,
                   context: Dict[str, Any] = None,
                   from_email: str = None,
                   cc: List[str] = None,
                   bcc: List[str] = None,
                   reply_to: str = None) -> bool:
        """
        Send email synchronously
        
        Args:
            recipient: Email address or list of addresses
            email_type: Predefined email type ('welcome', 'password_reset', etc.)
            subject: Email subject (used when not using email_type)
            html_body: HTML email body (used when not using email_type)
            text_body: Plain text body (optional)
            context: Template context for rendering
            from_email: Sender email address
            cc: CC recipients
            bcc: BCC recipients
            reply_to: Reply-to address
            
        Returns:
            bool: True if sent successfully
        """
        try:
            # Prepare recipients
            if isinstance(recipient, str):
                recipients = [recipient]
            else:
                recipients = recipient
            
            # Prepare email content
            if email_type:
                content = self._prepare_email_content(email_type, context or {})
                subject = content['subject']
                html_body = content['html_body']
                text_body = content['text_body']
            
            if not subject:
                raise ValueError("Subject is required")
            
            # Create email message
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_body or '',
                from_email=from_email or self.from_email,
                to=recipients,
                cc=cc or [],
                bcc=bcc or [],
                reply_to=[reply_to] if reply_to else None
            )
            
            # Add HTML alternative
            if html_body:
                email.attach_alternative(html_body, "text/html")
            
            # Send email
            email.send()
            
            logger.info(f"Email sent successfully to {recipients}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipients}: {str(e)}")
            raise
    
    def send_email_async(self, 
                        recipient: Union[str, List[str]],
                        email_type: str = None,
                        subject: str = None,
                        html_body: str = None,
                        text_body: str = None,
                        context: Dict[str, Any] = None,
                        from_email: str = None,
                        cc: List[str] = None,
                        bcc: List[str] = None,
                        reply_to: str = None,
                        delay_seconds: int = 0) -> str:
        """
        Send email asynchronously via Celery
        
        Args:
            Same as send_email()
            delay_seconds: Delay sending by N seconds
            
        Returns:
            str: Celery task ID
        """
        task_kwargs = {
            'recipient': recipient,
            'email_type': email_type,
            'subject': subject,
            'html_body': html_body,
            'text_body': text_body,
            'context': context,
            'from_email': from_email,
            'cc': cc,
            'bcc': bcc,
            'reply_to': reply_to
        }
        
        if delay_seconds > 0:
            task = send_email_celery_task.apply_async(
                kwargs=task_kwargs,
                countdown=delay_seconds
            )
        else:
            task = send_email_celery_task.delay(**task_kwargs)
        
        logger.info(f"Email queued for async sending: {task.id}")
        return task.id
    
    def send_welcome_email(self, recipient: str, user_name: str, 
                          site_name: str = "Our Platform", 
                          login_url: str = "/", **kwargs) -> Union[bool, str]:
        """Send welcome email"""
        context = {
            'user_name': user_name,
            'site_name': site_name,
            'login_url': login_url
        }
        
        if kwargs.get('async_send', True):
            return self.send_email_async(recipient, 'welcome', context=context, **kwargs)
        else:
            return self.send_email(recipient, 'welcome', context=context, **kwargs)
    
    def send_password_reset_email(self, recipient: str, user_name: str,
                                 reset_url: str, expires_in: int = 24, **kwargs) -> Union[bool, str]:
        """Send password reset email"""
        context = {
            'user_name': user_name,
            'reset_url': reset_url,
            'expires_in': expires_in
        }
        
        if kwargs.get('async_send', True):
            return self.send_email_async(recipient, 'password_reset', context=context, **kwargs)
        else:
            return self.send_email(recipient, 'password_reset', context=context, **kwargs)
    
    def send_notification_email(self, recipient: str, title: str, message: str,
                               action_url: str = None, action_text: str = "View Details",
                               **kwargs) -> Union[bool, str]:
        """Send notification email"""
        context = {
            'title': title,
            'message': message,
            'action_url': action_url,
            'action_text': action_text
        }
        
        if kwargs.get('async_send', True):
            return self.send_email_async(recipient, 'notification', context=context, **kwargs)
        else:
            return self.send_email(recipient, 'notification', context=context, **kwargs)
    
    def send_order_confirmation_email(self, recipient: str, customer_name: str,
                                     order_number: str, total_amount: str,
                                     delivery_date: str, tracking_url: str,
                                     **kwargs) -> Union[bool, str]:
        """Send order confirmation email"""
        context = {
            'customer_name': customer_name,
            'order_number': order_number,
            'total_amount': total_amount,
            'delivery_date': delivery_date,
            'tracking_url': tracking_url
        }
        
        if kwargs.get('async_send', True):
            return self.send_email_async(recipient, 'order_confirmation', context=context, **kwargs)
        else:
            return self.send_email(recipient, 'order_confirmation', context=context, **kwargs)


# Celery task
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_celery_task(self, **kwargs):
    """
    Celery task for sending emails asynchronously
    """
    try:
        email_service = EmailService()
        success = email_service.send_email(**kwargs)
        
        if success:
            logger.info(f"Async email sent successfully")
        
        return success
        
    except Exception as e:
        logger.error(f"Async email failed: {str(e)}")
        
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying email task (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60 * (self.request.retries + 1))
        
        raise


# Usage Examples:
"""
# Initialize service
email_service = EmailService()

# Send welcome email (async by default)
task_id = email_service.send_welcome_email(
    recipient='user@example.com',
    user_name='John Doe',
    site_name='MyApp'
)

# Send password reset (sync)
success = email_service.send_password_reset_email(
    recipient='user@example.com',
    user_name='John Doe',
    reset_url='https://myapp.com/reset/abc123',
    async_send=False
)

# Send custom email
email_service.send_email(
    recipient='user@example.com',
    subject='Custom Subject',
    html_body='<h1>Custom HTML Content</h1>',
    text_body='Custom text content'
)

# Send notification
email_service.send_notification_email(
    recipient='admin@example.com',
    title='Credentials updated successful',
    message='A new user has registered on the platform.',
    action_url='https://admin.myapp.com/users',
    action_text='View User'
)
"""