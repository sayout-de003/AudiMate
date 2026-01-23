from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class UserProfileView(LoginRequiredMixin, TemplateView):
    template_name = "settings/profile.html"
