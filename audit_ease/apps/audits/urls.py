"""
Audit API URLs

All endpoints are organization-isolated and require authentication.
Every request is verified against the user's organization membership.
"""

from django.urls import path
from .views import (
    AuditStartView,
    AuditDetailView,
    AuditEvidenceView,
    AuditListView,
    DashboardSummaryView,
    DashboardStatsView,
    AuditSnapshotCreateView,
    AuditSnapshotListView,
    AuditSnapshotDetailView,
)
from .views_export import export_audit_csv_streaming, ExportAuditReportView

app_name = 'audits'

urlpatterns = [
    # List all audits for user's organization
    path('', AuditListView.as_view(), name='audit-list'),
    
    # Start a new audit for user's organization
    path('start/', AuditStartView.as_view(), name='audit-start'),
    
    # Get details of a specific audit
    path('<uuid:audit_id>/', AuditDetailView.as_view(), name='audit-detail'),
    
    # Get evidence/findings from an audit
    path('<uuid:audit_id>/evidence/', AuditEvidenceView.as_view(), name='audit-evidence'),
    
    # Export audit as CSV (Premium feature)
    path('<uuid:audit_id>/export/csv/', export_audit_csv_streaming, name='audit-export-csv'),
    path('<uuid:audit_id>/export/xlsx/', ExportAuditReportView.as_view(), name='audit-export-xlsx'),
    
    # Executive dashboard summary with aggregated stats
    path('dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),

    # Snapshots
    path('<uuid:audit_id>/snapshots/', AuditSnapshotListView.as_view(), name='audit-snapshot-list'),
    path('<uuid:audit_id>/snapshots/create/', AuditSnapshotCreateView.as_view(), name='audit-snapshot-create'),
    path('snapshots/<int:pk>/', AuditSnapshotDetailView.as_view(), name='audit-snapshot-detail'),

]