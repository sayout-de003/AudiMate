from rest_framework import serializers
from .models import Audit, Evidence, Question, AuditSnapshot, SecuritySnapshot

class AuditSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source='organization.name',
        read_only=True,
        help_text="Organization name for reference"
    )
    triggered_by_email = serializers.EmailField(
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
    screenshot_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Evidence
        fields = ['id', 'question', 'status', 'raw_data', 'comment', 'created_at', 'screenshot_url', 'remediation_steps']
        read_only_fields = ['id', 'created_at']

    def get_screenshot_url(self, obj):
        if obj.screenshot:
            return obj.screenshot.url
        return None

    def validate_raw_data(self, value):
        """
        Ensure raw_data is a valid dictionary and not too massive.
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError("raw_data must be a valid JSON object.")
        # Optional: Safety check for size (naive approach)
        import json
        if len(json.dumps(value)) > 100000: # 100KB limit example
             raise serializers.ValidationError("raw_data payload is too large.")
        return value

class AuditSnapshotSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(
        source='created_by.email',
        read_only=True,
        help_text="Email of user who created the snapshot"
    )
    
    class Meta:
        model = AuditSnapshot
        fields = ['id', 'audit', 'name', 'version', 'checksum', 'created_at', 'created_by_email']
        read_only_fields = ['id', 'audit', 'version', 'checksum', 'created_at', 'created_by_email']

class SecuritySnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecuritySnapshot
        fields = ['date', 'score', 'grade', 'critical_count']

class AuditSnapshotDetailSerializer(AuditSnapshotSerializer):
    class Meta(AuditSnapshotSerializer.Meta):
        fields = AuditSnapshotSerializer.Meta.fields + ['data']

class AuditSnapshotCreateSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=255, 
        required=False,
        help_text="Optional name for the snapshot. Auto-generated if blank."
    )

class EvidenceCreateSerializer(serializers.ModelSerializer):
    question_id = serializers.PrimaryKeyRelatedField(
        queryset=Question.objects.all(),
        source='question',
        write_only=True
    )
    
    class Meta:
        model = Evidence
        fields = ['question_id', 'status', 'raw_data', 'comment']

class EvidenceUploadSerializer(serializers.Serializer):
    session_id = serializers.UUIDField(help_text="The ID of the session (Audit) to append evidence to.")
    evidence_type = serializers.ChoiceField(choices=[('screenshot', 'Screenshot'), ('log', 'Log')], help_text="Type of evidence artifact.")
    data = serializers.JSONField(help_text="Raw evidence data. For logs, JSON is required. For screenshots, binary data is likely handled differently (but treating as JSON/Base64 for now per prompt hint 'data').")

    def validate_session_id(self, value):
        if not Audit.objects.filter(id=value).exists():
             raise serializers.ValidationError("Session does not exist.")
        return value

class EvidenceMilestoneSerializer(serializers.Serializer):
    session_id = serializers.UUIDField(help_text="The ID of the session to create a milestone for.")
    title = serializers.CharField(max_length=255, help_text="Title of the milestone.")
    description = serializers.CharField(required=False, allow_blank=True, help_text="Description of the event/milestone.")
    timestamp = serializers.DateTimeField(required=False, help_text="Optional timestamp overriding now.")

    def validate_session_id(self, value):
        if not Audit.objects.filter(id=value).exists():
            raise serializers.ValidationError("Session does not exist.")
        return value