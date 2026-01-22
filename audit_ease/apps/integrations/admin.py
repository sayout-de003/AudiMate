from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Integration

@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "provider", "created_at")
    
    # Exclude the raw binary field so admins can't break it
    exclude = ("_encrypted_token",) 
    
    # Optional: Add a readonly field to show *if* a token exists, without showing the token
    readonly_fields = ("has_token",)

    def has_token(self, obj):
        return obj.token is not None
    has_token.boolean = True