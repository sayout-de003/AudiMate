# Production Deployment Guide

## Pre-Deployment Checklist

### 1. Environment Setup

```bash
# Generate encryption keys (do this ONCE per production environment)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Output (example):
# gAAAAABlzJ8kw2n4...rest_of_key...5jDq_U=

# Save this securely in your environment management system
# AWS Secrets Manager, HashiCorp Vault, or similar
```

### 2. Environment Variables (Production)

```bash
# Critical - Must be set before application startup
export FERNET_KEY_PRIMARY='gAAAAABlzJ8kw2n4...5jDq_U='
export FERNET_KEYS_HISTORICAL=''  # Empty on first deployment
export FERNET_KEY_CREATED_AT='2026-01-20T10:30:00'

# Database
export DATABASE_URL='postgresql://user:pass@host:5432/audit_ease'

# Django
export DJANGO_DEBUG='False'
export DJANGO_SECRET_KEY='your-secret-key-here'

# Celery (async task processing)
export CELERY_BROKER_URL='redis://localhost:6379/0'
export CELERY_RESULT_BACKEND='redis://localhost:6379/0'

# API Settings
export ALLOWED_HOSTS='api.example.com,www.example.com'
export CORS_ALLOWED_ORIGINS='https://app.example.com'
```

### 3. Database Migrations

```bash
# Navigate to project directory
cd /Users/sayantande/audit_full_app/audit_ease

# Apply all migrations
python manage.py migrate

# Create audit categories (if using fixtures)
python manage.py loaddata apps/audits/fixtures/initial_questions.json

# Verify migrations
python manage.py showmigrations
```

### 4. Initial Data Setup

```bash
# Create superuser for admin panel
python manage.py createsuperuser

# Seed initial organizations (optional)
python manage.py loaddata apps/organizations/fixtures/initial_orgs.json

# Create default audit questions
python manage.py shell
```

```python
from apps.audits.models import Question

questions = [
    {
        'key': 'github_2fa',
        'title': 'Two-Factor Authentication Enforced',
        'description': 'Verify 2FA is mandatory for all organization members',
        'severity': 'CRITICAL'
    },
    {
        'key': 'github_branch_protection',
        'title': 'Branch Protection Rules Configured',
        'description': 'Main branch requires code review and status checks',
        'severity': 'HIGH'
    },
    {
        'key': 'github_secret_scanning',
        'title': 'Secret Scanning Enabled',
        'description': 'Repository scans for accidentally committed secrets',
        'severity': 'HIGH'
    },
    {
        'key': 'github_org_members',
        'title': 'Organization Members Verified',
        'description': 'Confirm organization has expected members',
        'severity': 'MEDIUM'
    }
]

for q_data in questions:
    Question.objects.get_or_create(**q_data)

print("Questions created successfully")
```

### 5. Security Verification

```bash
# Run security checks
python manage.py check --deploy

# Run tests
python manage.py test apps.audits apps.integrations apps.organizations apps.users

# Check encryption setup
python manage.py shell
```

```python
from services.encryption_manager import get_key_manager

manager = get_key_manager()
status = manager.get_key_status()
print(status)
# Should show: primary_key_set=True, key_age_days=0, rotation_required=False
```

---

## Deployment Steps

### Using Docker (Recommended)

```bash
# Build image
docker build -t audit_ease:latest .

# Run container
docker run -d \
  -e FERNET_KEY_PRIMARY='gAAAAABlzJ8k...' \
  -e DATABASE_URL='postgresql://...' \
  -e CELERY_BROKER_URL='redis://...' \
  -p 8000:8000 \
  audit_ease:latest

# Run migrations in container
docker exec <container_id> python manage.py migrate

# Create superuser
docker exec -it <container_id> python manage.py createsuperuser
```

### Manual Deployment (Linux/Unix)

```bash
# 1. Clone repository
cd /opt/audit_ease
git clone https://github.com/yourepo/audit_ease.git .

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
source /etc/audit_ease/.env  # Your secure env file

# 5. Run migrations
python manage.py migrate

# 6. Collect static files
python manage.py collectstatic --noinput

# 7. Start application (with gunicorn)
gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --worker-class=sync \
  --max-requests=1000

# 8. Start Celery worker (for async tasks)
celery -A config worker -l info
```

### Nginx Configuration (Reverse Proxy)

```nginx
upstream audit_ease {
    server 127.0.0.1:8000;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;
    
    ssl_certificate /etc/ssl/certs/api.example.com.crt;
    ssl_certificate_key /etc/ssl/private/api.example.com.key;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self'" always;
    
    # CORS
    add_header Access-Control-Allow-Origin "https://app.example.com" always;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
    
    location /api/ {
        proxy_pass http://audit_ease;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location /static/ {
        alias /opt/audit_ease/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable" always;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name api.example.com;
    return 301 https://$server_name$request_uri;
}
```

---

## Post-Deployment Verification

### Health Checks

```bash
# Check API is responding
curl -X GET https://api.example.com/api/v1/audits/ \
  -H "Authorization: Bearer TOKEN"

# Should return: {"audit_count": 0, "audits": []}

# Check admin panel
curl https://api.example.com/admin/
# Should redirect to login page
```

### Database Verification

```bash
# Connect to database
psql $DATABASE_URL

# Check tables exist
\dt apps_audit*

# Verify organization isolation
SELECT COUNT(*) FROM apps_audits_audit;
# Should be 0 (no data yet)

# Check integration tokens are encrypted
SELECT id, provider, _access_token FROM apps_integrations_integration LIMIT 1;
# _access_token should be binary/encrypted data
```

### Log Monitoring

```bash
# Watch application logs
tail -f /var/log/audit_ease/django.log

# Watch key rotation logs
tail -f /var/log/audit_ease/key_rotation.json

# Expected on startup:
# - "Application started successfully"
# - "Encryption key manager initialized"
# - "FERNET_KEY_PRIMARY loaded (not shown for security)"
```

---

## Monitoring & Alerting

### Key Metrics Dashboard

```python
# apps/audits/management/commands/health_check.py

from django.core.management.base import BaseCommand
from apps.audits.models import Audit
from services.encryption_manager import get_key_manager

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Audit metrics
        audits_today = Audit.objects.filter(
            created_at__date=timezone.now().date()
        ).count()
        
        # Encryption metrics
        manager = get_key_manager()
        key_status = manager.get_key_status()
        
        print({
            'audits_today': audits_today,
            'key_rotation_required': key_status['rotation_required'],
            'days_until_rotation': key_status['days_until_rotation'],
        })
```

### Alert Rules (Prometheus/Alertmanager)

```yaml
groups:
  - name: audit_ease
    rules:
      - alert: KeyRotationDue
        expr: audit_ease_key_age_days > 85
        for: 1h
        annotations:
          summary: "Encryption key rotation due in {{ $value }} days"
          action: "Run: python manage.py rotate_encryption_keys"
      
      - alert: HighFailureRate
        expr: rate(audit_ease_check_failures_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: "Audit failure rate is {{ $value | humanizePercentage }}"
      
      - alert: DecryptionFailures
        expr: audit_ease_decryption_failures_total > 0
        for: 1m
        annotations:
          summary: "Token decryption failures detected - check encryption key"
```

---

## Key Rotation (Scheduled)

### Automated Rotation Script

```bash
#!/bin/bash
# /opt/audit_ease/scripts/rotate_keys_monthly.sh

set -e

cd /opt/audit_ease
source venv/bin/activate

# Perform rotation
python manage.py rotate_encryption_keys

# Commit new keys to vault
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "Key rotation completed at $TIMESTAMP"

# Restart application
systemctl restart audit_ease_gunicorn
systemctl restart audit_ease_celery

echo "Application restarted with new keys"
```

### Crontab Setup

```bash
# Rotate keys on the 1st of each month at 2 AM
0 2 1 * * /opt/audit_ease/scripts/rotate_keys_monthly.sh >> /var/log/audit_ease/cron.log 2>&1
```

---

## Troubleshooting

### Application Won't Start

```bash
# Check environment variables
env | grep FERNET_KEY_PRIMARY

# Verify encryption key is valid
python3 -c "from cryptography.fernet import Fernet; Fernet('$FERNET_KEY_PRIMARY')"

# Run migrations
python manage.py migrate

# Check for errors
python manage.py check --deploy
```

### Permission Denied Errors

```bash
# Verify user can access organization
python manage.py shell
```

```python
from apps.users.models import User
from apps.organizations.models import Membership

user = User.objects.first()
membership = Membership.objects.filter(user=user).first()
print(f"User: {user.email}, Org: {membership.organization.name}, Role: {membership.role}")
```

### GitHub Integration Fails

```python
# Test GitHub connection
from services.github_service import GitHubService
from apps.integrations.models import Integration

integration = Integration.objects.filter(provider='github').first()
service = GitHubService(integration)

# This should work without throwing exception
try:
    service._verify_authentication()
    print("GitHub authentication successful")
except Exception as e:
    print(f"GitHub auth failed: {e}")
```

---

## Backup & Recovery

### Database Backup

```bash
# Daily backup
pg_dump $DATABASE_URL | gzip > /backups/audit_ease_$(date +%Y%m%d).sql.gz

# Restore
gunzip < /backups/audit_ease_20260120.sql.gz | psql $DATABASE_URL
```

### Encryption Key Backup

```bash
# CRITICAL: Keep encryption keys in secure backup
# Never commit to Git, only store in secure vault

aws secretsmanager create-secret \
  --name audit_ease/encryption_keys_backup \
  --secret-string file:///secure/location/keys.json
```

```json
{
  "FERNET_KEY_PRIMARY": "gAAAAABlzJ8k...",
  "FERNET_KEYS_HISTORICAL": ["...", "..."],
  "FERNET_KEY_CREATED_AT": "2026-01-20T10:30:00",
  "backup_date": "2026-01-20T15:00:00"
}
```

---

## Support Contacts

- **Security Issues**: security@example.com
- **Deployment Help**: devops@example.com
- **Bug Reports**: issues@example.com

---

Version: 1.0
Last Updated: 2026-01-20
Environment: Production
Status: Ready for Launch
