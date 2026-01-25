from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuditViewSet
from ..views import (
    DashboardSummaryView,
    DashboardStatsView,
    AuditSnapshotCreateView,
    AuditSnapshotListView,
    AuditSnapshotDetailView,
    EvidenceCreateView,
    EvidenceUploadView,
    EvidenceMilestoneView,
    SessionFinalizeView,
)

router = DefaultRouter()
router.register(r'audits', AuditViewSet, basename='audits')

# Specialized paths that don't fit into the main audits/ router elegantly or were legacy
specialized_urlpatterns = [
    # Dashboard (Not specific to one audit)
    path('audits/dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard-summary-legacy'),
    path('audits/dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats-legacy'),

    # Snapshots (Legacy paths - though ViewSet could handle some, keeping for compatibility)
    path('audits/<uuid:audit_id>/snapshots/', AuditSnapshotListView.as_view(), name='audit-snapshot-list-legacy'),
    path('audits/<uuid:audit_id>/snapshots/create/', AuditSnapshotCreateView.as_view(), name='audit-snapshot-create-legacy'),
    path('audits/snapshots/<int:pk>/', AuditSnapshotDetailView.as_view(), name='audit-snapshot-detail-legacy'),
    
    # Evidence & Sessions
    path('audits/evidence/upload/', EvidenceUploadView.as_view(), name='evidence-upload-legacy'),
    path('audits/evidence/milestone/', EvidenceMilestoneView.as_view(), name='evidence-milestone-legacy'),
    path('audits/session/<uuid:pk>/finalize/', SessionFinalizeView.as_view(), name='session-finalize-legacy'),
]

urlpatterns = [
    # Legacy/Specialized patterns
    *specialized_urlpatterns,
    
    # Router handles /audits/, /audits/<id>/, /audits/<id>/export/csv/, /audits/start/, /audits/<id>/evidence/
    path('', include(router.urls)),
]
