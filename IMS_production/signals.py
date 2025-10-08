from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Sale, SalesSummary

@receiver(post_save, sender=Sale, dispatch_uid='update_sales_summary')
def update_sales_summary(sender, instance, created, **kwargs):
    # Use `get_or_create` to retrieve or create a SalesSummary
    summary, created_summary = SalesSummary.objects.get_or_create(
        product=instance.product,
        defaults={
            'total_sold': instance.total_amount,
            'total_revenue': instance.total_revenue
        }
    )
            
        
