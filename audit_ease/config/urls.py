# config/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Delegate all API routes to their respective apps
    path('api/v1/', include('apps.users.urls')),
    path('api/v1/', include('apps.organizations.urls')),
    path('api/v1/integrations/', include('apps.integrations.urls')),
    path('api/v1/audits/', include('apps.audits.urls')),
    path('api/v1/reports/', include('apps.reports.urls')),
    path('api/v1/billing/', include('apps.billing.urls')),
    
]