
# config/urls.py
from django.contrib import admin
from django.urls import path, include

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

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

    # Delegate all API routes to their respective apps
    path("api/v1/", include("apps.users.urls")),
    path("api/v1/", include("apps.organizations.urls")),
    path("api/v1/integrations/", include("apps.integrations.urls")),
    path("api/v1/audits/", include("apps.audits.urls")),
    path("api/v1/reports/", include("apps.reports.urls")),
    path("api/v1/billing/", include("apps.billing.urls")),
    path("debug-sentry/", trigger_error),

    # Frontend Views
    path("settings/audit-log/", include("apps.organizations.urls_frontend")),
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


