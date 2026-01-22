#!/bin/bash

# AuditEase Production Environment Setup
# This script ensures all required production environment variables are configured.
# Run this before deploying to production.

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          AuditEase Production Environment Setup               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file already exists. Backing up to .env.backup${NC}"
    cp .env .env.backup
    echo -e "${GREEN}✓ Backup created at .env.backup${NC}"
    echo ""
fi

echo "Creating .env file with production configuration..."
echo ""

# Function to generate Fernet key
generate_fernet_key() {
    python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
}

# Function to generate Django secret key
generate_django_secret() {
    python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
}

# Prompt for required variables
echo "📋 Please provide the following required configuration:"
echo ""

# FERNET_KEY_PRIMARY
echo -e "${YELLOW}1. FERNET_KEY_PRIMARY (Encryption key for secure token storage)${NC}"
echo "   Press Enter to auto-generate a secure key, or paste an existing one:"
read -p "   > " FERNET_KEY_INPUT

if [ -z "$FERNET_KEY_INPUT" ]; then
    echo "   Generating secure Fernet key..."
    FERNET_KEY=$(generate_fernet_key)
    echo -e "   ${GREEN}✓ Generated:${NC} ${FERNET_KEY:0:20}..."
else
    FERNET_KEY="$FERNET_KEY_INPUT"
fi
echo ""

# DJANGO_SECRET_KEY
echo -e "${YELLOW}2. DJANGO_SECRET_KEY (Secret key for Django)${NC}"
echo "   Press Enter to auto-generate a secure key, or paste an existing one:"
read -p "   > " SECRET_KEY_INPUT

if [ -z "$SECRET_KEY_INPUT" ]; then
    echo "   Generating secure Django secret key..."
    DJANGO_SECRET_KEY=$(generate_django_secret)
    echo -e "   ${GREEN}✓ Generated:${NC} ${DJANGO_SECRET_KEY:0:20}..."
else
    DJANGO_SECRET_KEY="$SECRET_KEY_INPUT"
fi
echo ""

# DATABASE_URL
echo -e "${YELLOW}3. DATABASE_URL (PostgreSQL connection string)${NC}"
echo "   Format: postgresql://user:password@localhost:5432/dbname"
echo "   Or: postgresql+psycopg2://user:password@localhost:5432/dbname"
read -p "   > " DATABASE_URL

while [ -z "$DATABASE_URL" ]; do
    echo -e "${RED}✗ DATABASE_URL is required${NC}"
    read -p "   > " DATABASE_URL
done
echo -e "   ${GREEN}✓ Database URL configured${NC}"
echo ""

# Optional AWS credentials
echo -e "${YELLOW}4. AWS Credentials (Optional - leave blank to skip)${NC}"
read -p "   AWS_ACCESS_KEY_ID (optional): " AWS_ACCESS_KEY_ID
read -p "   AWS_SECRET_ACCESS_KEY (optional): " AWS_SECRET_ACCESS_KEY
read -p "   AWS_DEFAULT_REGION (default: us-east-1): " AWS_DEFAULT_REGION
AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
echo ""

# Optional GitHub token
echo -e "${YELLOW}5. GitHub Integration (Optional - leave blank to skip)${NC}"
read -p "   GITHUB_OAUTH_TOKEN (optional): " GITHUB_OAUTH_TOKEN
echo ""

# Django settings
echo -e "${YELLOW}6. Django Configuration${NC}"
read -p "   DJANGO_DEBUG (true/false, default: false): " DJANGO_DEBUG
DJANGO_DEBUG=${DJANGO_DEBUG:-false}
read -p "   DJANGO_ALLOWED_HOSTS (comma-separated, e.g., localhost,example.com): " DJANGO_ALLOWED_HOSTS
DJANGO_ALLOWED_HOSTS=${DJANGO_ALLOWED_HOSTS:-localhost}
echo ""

# Celery configuration
echo -e "${YELLOW}7. Celery/Redis Configuration${NC}"
read -p "   CELERY_BROKER_URL (default: redis://localhost:6379/0): " CELERY_BROKER_URL
CELERY_BROKER_URL=${CELERY_BROKER_URL:-redis://localhost:6379/0}
read -p "   CELERY_RESULT_BACKEND (default: redis://localhost:6379/1): " CELERY_RESULT_BACKEND
CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND:-redis://localhost:6379/1}
echo ""

# Create .env file
cat > .env << EOF
# =============================================================================
# AuditEase Production Configuration
# Generated: $(date)
# =============================================================================

# CRITICAL: Encryption for secure token storage
FERNET_KEY=${FERNET_KEY}
ENCRYPTION_KEY=${FERNET_KEY}

# CRITICAL: Django security
DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
DJANGO_DEBUG=${DJANGO_DEBUG}
DJANGO_ALLOWED_HOSTS=${DJANGO_ALLOWED_HOSTS}

# CRITICAL: Database connection
DATABASE_URL=${DATABASE_URL}

# AWS Integration (Optional)
EOF

if [ -n "$AWS_ACCESS_KEY_ID" ]; then
    cat >> .env << EOF
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION}
EOF
fi

if [ -n "$GITHUB_OAUTH_TOKEN" ]; then
    cat >> .env << EOF

# GitHub Integration
GITHUB_OAUTH_TOKEN=${GITHUB_OAUTH_TOKEN}
EOF
fi

cat >> .env << EOF

# Celery/Redis Configuration
CELERY_BROKER_URL=${CELERY_BROKER_URL}
CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND}

# Time Zone
TIME_ZONE=UTC

# Logging
LOG_LEVEL=INFO

# Email Configuration (Optional - for notifications)
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# EMAIL_HOST=smtp.gmail.com
# EMAIL_PORT=587
# EMAIL_USE_TLS=true
# EMAIL_HOST_USER=your-email@gmail.com
# EMAIL_HOST_PASSWORD=your-app-password

# =============================================================================
# DO NOT COMMIT THIS FILE TO VERSION CONTROL
# =============================================================================
EOF

echo -e "${GREEN}✓ .env file created successfully${NC}"
echo ""

# Create .env.example if it doesn't exist
if [ ! -f .env.example ]; then
    cat > .env.example << 'EOF'
# AuditEase Production Configuration Template
# Copy this file to .env and fill in your values

# CRITICAL: Encryption for secure token storage (Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
FERNET_KEY=<your-fernet-key-here>
ENCRYPTION_KEY=<your-fernet-key-here>

# CRITICAL: Django security (Generate with: python manage.py shell -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
DJANGO_SECRET_KEY=<your-django-secret-key-here>
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=localhost,example.com

# CRITICAL: Database connection
DATABASE_URL=postgresql://user:password@localhost:5432/audit_ease_db

# AWS Integration (Optional)
AWS_ACCESS_KEY_ID=<your-aws-access-key>
AWS_SECRET_ACCESS_KEY=<your-aws-secret-key>
AWS_DEFAULT_REGION=us-east-1

# GitHub Integration (Optional)
GITHUB_OAUTH_TOKEN=<your-github-oauth-token>

# Celery/Redis Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Time Zone
TIME_ZONE=UTC

# Logging
LOG_LEVEL=INFO
EOF
    echo -e "${GREEN}✓ .env.example template created for documentation${NC}"
    echo ""
fi

# Verify critical settings
echo "🔍 Verifying configuration..."
echo ""

ERRORS=0

if [ -z "$FERNET_KEY" ]; then
    echo -e "${RED}✗ FERNET_KEY is required${NC}"
    ERRORS=$((ERRORS + 1))
fi

if [ -z "$DJANGO_SECRET_KEY" ]; then
    echo -e "${RED}✗ DJANGO_SECRET_KEY is required${NC}"
    ERRORS=$((ERRORS + 1))
fi

if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}✗ DATABASE_URL is required${NC}"
    ERRORS=$((ERRORS + 1))
fi

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ All critical configuration variables are set${NC}"
    echo -e "${GREEN}✓ Environment setup complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Review the .env file for any adjustments"
    echo "  2. Run migrations: python manage.py migrate"
    echo "  3. Create a superuser: python manage.py createsuperuser"
    echo "  4. Start the server: python manage.py runserver"
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANT: Never commit .env to version control!${NC}"
    echo -e "${YELLOW}⚠️  Keep .env.example up-to-date without sensitive values${NC}"
else
    echo -e "${RED}✗ Configuration failed with $ERRORS errors${NC}"
    exit 1
fi
