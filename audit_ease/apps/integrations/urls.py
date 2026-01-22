from django.urls import path
from .views import GithubConnectView, GithubCallbackView, GitHubWebhookView

urlpatterns = [
    path('github/connect/', GithubConnectView.as_view(), name='github_connect'),
    path('github/callback/', GithubCallbackView.as_view(), name='github_callback'),
]

# Webhook endpoints (different routing)
webhook_patterns = [
    path('webhooks/github/', GitHubWebhookView.as_view(), name='github_webhook'),
]

urlpatterns += webhook_patterns