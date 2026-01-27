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
    AuditSnapshotListView,
    AuditSnapshotDetailView,
    EvidenceCreateView,
    EvidenceUploadView,
    EvidenceMilestoneView,
    SessionFinalizeView,
    EvidenceScreenshotUploadView,
    RiskAcceptanceCreateView,
)
from .views_export import AuditExportCSVView, ExportAuditReportView, AuditExportPDFView, AuditExportPreviewView
app_name = 'audits'

urlpatterns = [
    # List all audits for user's organization
    path('', AuditListView.as_view(), name='audit-list'),
    
    # Start a new audit for user's organization
    path('start/', AuditStartView.as_view(), name='audit-start'),
    
    # Get details of a specific audit
    path('<uuid:audit_id>/', AuditDetailView.as_view(), name='audit-detail'),
    
    # Get evidence/findings from an audit
    # Get evidence/findings from an audit
    path('<uuid:audit_id>/evidence/', AuditEvidenceView.as_view(), name='audit-evidence'),
    path('<uuid:audit_id>/evidence/create/', EvidenceCreateView.as_view(), name='audit-evidence-create'),
    
    # Export audit as CSV (Premium feature)
    path('<uuid:audit_id>/export/csv/', AuditExportCSVView.as_view(), name='audit-export-csv'),
    path('<uuid:audit_id>/export/xlsx/', ExportAuditReportView.as_view(), name='audit-export-xlsx'),
    path('<uuid:audit_id>/export/pdf/', AuditExportPDFView.as_view(), name='audit-export-pdf'),
    path('<uuid:audit_id>/export/preview/', AuditExportPreviewView.as_view(), name='audit-export-preview'),
    
    # Executive dashboard summary with aggregated stats
    path('dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),

    # Snapshots
    path('<uuid:audit_id>/snapshots/', AuditSnapshotListView.as_view(), name='audit-snapshot-list'),
    path('<uuid:audit_id>/snapshots/create/', AuditSnapshotCreateView.as_view(), name='audit-snapshot-create'),
    path('snapshots/<int:pk>/', AuditSnapshotDetailView.as_view(), name='audit-snapshot-detail'),
    
    # Evidence & Compliance Endpoints (New Terminology)
    path('evidence/upload/', EvidenceUploadView.as_view(), name='evidence-upload'),
    path('evidence/milestone/', EvidenceMilestoneView.as_view(), name='evidence-milestone'),
    path('session/<uuid:pk>/finalize/', SessionFinalizeView.as_view(), name='session-finalize'),
    path('evidence/<int:pk>/upload_screenshot/', EvidenceScreenshotUploadView.as_view(), name='evidence-upload-screenshot'),

 
    # Risk Acceptance
    path('risk-accept/', RiskAcceptanceCreateView.as_view(), name='risk-accept'),
]
