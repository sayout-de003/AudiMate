from rest_framework import serializers
from .models import Audit, Evidence, Question

class AuditSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source='organization.name',
        read_only=True,
        help_text="Organization name for reference"
    )
    triggered_by_email = serializers.CharField(
        source='triggered_by.email',
        read_only=True,
        allow_null=True,
        help_text="Email of user who triggered this audit"
    )
    
    class Meta:
        model = Audit
        fields = [
            'id', 'organization', 'organization_name', 'status', 
            'triggered_by', 'triggered_by_email',
            'created_at', 'completed_at'
        ]
        read_only_fields = ['id', 'organization', 'triggered_by', 'created_at', 'completed_at']

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'key', 'title', 'description', 'severity']
        read_only_fields = ['id']

class EvidenceSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)
    
    class Meta:
        model = Evidence
        fields = ['id', 'question', 'status', 'raw_data', 'comment', 'created_at']
        read_only_fields = ['id', 'created_at']