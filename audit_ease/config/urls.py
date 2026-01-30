from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from apps.users.views_frontend import UserProfileView
from rest_framework.routers import SimpleRouter, DefaultRouter

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
router = SimpleRouter()
from config.views import custom_500, health_check

handler500 = 'config.views.custom_500'

from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def trigger_error(request):
    division_by_zero = 1 / 0

urlpatterns = [
    path("admin/", admin.site.urls),

    # OpenAPI schema (JSON)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),

    # Swagger UI
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),

    # ReDoc UI
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),

    # Health Check
    path("health/", health_check, name="health_check"),

    # Delegate all API routes to their respective apps
    path("api/v1/", include("apps.users.urls")),
    path("api/v1/", include("apps.organizations.urls")),
    path("api/v1/integrations/", include("apps.integrations.urls")),
    path("api/v1/audits/", include("apps.audits.urls")),
    path("api/v1/reports/", include("apps.reports.urls")),
    path("api/v1/billing/", include("apps.billing.urls")),
    path("debug-sentry/", trigger_error),

    # AllAuth URLs
    path("accounts/", include("allauth.urls")),
    
    # DJ-REST-AUTH URLs
    path("api/v1/auth/", include("dj_rest_auth.urls")),
    path("api/v1/auth/registration/", include("dj_rest_auth.registration.urls")),

    # Frontend Views
    path("settings/audit-log/", include("apps.organizations.urls_frontend")),
    path("settings/profile/", UserProfileView.as_view(), name="user-profile"),
    path("privacy-policy/", TemplateView.as_view(template_name="legal/privacy_policy.html"), name="privacy_policy"),
]














# # config/urls.py
# from django.contrib import admin
# from django.urls import path, include

# urlpatterns = [
#     path('admin/', admin.site.urls),
    
#     # Delegate all API routes to their respective apps
#     path('api/v1/', include('apps.users.urls')),
#     path('api/v1/', include('apps.organizations.urls')),
#     path('api/v1/integrations/', include('apps.integrations.urls')),
#     path('api/v1/audits/', include('apps.audits.urls')),
#     path('api/v1/reports/', include('apps.reports.urls')),
#     path('api/v1/billing/', include('apps.billing.urls')),
    
# ]


