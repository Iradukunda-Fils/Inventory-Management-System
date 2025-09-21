"""
URL configuration for Inventory_MS project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

#-----------------------<> IMPORTS FOR MEDIA URL IN MY CONF <>----------------------#
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse



urlpatterns = [
    path('adn/', admin.site.urls),
    path('',include('authentication.urls')),
    path('admin-dashboard/',include('IMS_admin.urls')),
    path('staff-dashboard/',include('IMS_staff.urls')),
    path('info/',include('IMS_production.urls')),
]

urlpatterns += [
    path("health/", lambda request: JsonResponse({"status": "ok"}), name="health_check"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)