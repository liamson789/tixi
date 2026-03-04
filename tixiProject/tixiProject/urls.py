"""
URL configuration for tixiProject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from django.views.generic import RedirectView
from accounts.views import profile_view
from payments.webhooks import wompi_webhook
from payments.views import payment_return, payment_status
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/password/reset/', RedirectView.as_view(pattern_name='account_login', permanent=False), name='account_reset_password'),
    path('accounts/profile/', profile_view, name='user_profile'),
    path('accounts/', include('allauth.urls')),
    path('', include('raffles.urls')),
    path('raffles/', include('raffles.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('webhook/wompi/', wompi_webhook),
    path('payment/return', payment_return, name='payment_return'),
    path('payment/status', payment_status, name='payment_status'),
]

# Servir archivos de media en desarrollo
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()

if settings.DEBUG or getattr(settings, 'SERVE_MEDIA', False):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
