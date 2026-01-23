from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GithubConnectView, GithubCallbackView, GitHubWebhookView, IntegrationViewSet

router = DefaultRouter()
router.register(r'', IntegrationViewSet, basename='integration')

urlpatterns = [
    path('github/connect/', GithubConnectView.as_view(), name='github_connect'),
    path('github/callback/', GithubCallbackView.as_view(), name='github_callback'),
    path('', include(router.urls)),
]

# Webhook endpoints (different routing)
webhook_patterns = [
    path('webhooks/github/', GitHubWebhookView.as_view(), name='github_webhook'),
]

urlpatterns += webhook_patterns