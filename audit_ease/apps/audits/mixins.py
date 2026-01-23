from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.contrib import messages
from allauth.socialaccount.models import SocialAccount

class RequireGitHubTokenMixin(AccessMixin):
    """
    Mixin to enforce that the user has a linked GitHub account.
    If not, redirects to the user profile settings page with a warning.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not SocialAccount.objects.filter(user=request.user, provider='github').exists():
            messages.warning(request, "You must connect your GitHub account to run an audit.")
            return redirect("user-profile")

        return super().dispatch(request, *args, **kwargs)
