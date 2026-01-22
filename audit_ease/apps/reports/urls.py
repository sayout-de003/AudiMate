# apps/reports/urls.py
from django.urls import path
from .views import AuditReportPDFView

urlpatterns = [
    path('<int:id>/pdf/', AuditReportPDFView.as_view(), name='audit-report-pdf'),
]