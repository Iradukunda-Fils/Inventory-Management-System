from django.apps import AppConfig

class ImsProductionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'IMS_production'
    
    def ready(self):
        # Correctly import signals
        import IMS_production.signals
