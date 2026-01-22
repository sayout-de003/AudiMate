# Project Documentation

## Directory Structure

```
/
├───db.sqlite3
├───README.md
├───aud/
└───audit_ease/
    ├───.env.example
    ├───.gitignore
    ├───ARCHITECTURE.md
    ├───celery_app.py
    ├───CHANGELOG.md
    ├───DEPLOYMENT.md
    ├───docker-compose.yml
    ├───Dockerfile
    ├───entrypoint.sh
    ├───IMPLEMENTATION_SUMMARY.md
    ├───LAUNCH_CHECKLIST.md
    ├───manage.py
    ├───production_env_setup.sh
    ├───pyproject.toml
    ├───QUICK_REFERENCE.md
    ├───README_SAAS.md
    ├───README_SECURITY_IMPLEMENTATION.md
    ├───README.md
    ├───requirements.txt
    ├───SAAS_TRANSFORMATION.md
    ├───SECURITY.md
    ├───SETUP_COMPLETE.md
    ├───verify_phase3.py
    ├───apps/
    │   ├───__init__.py
    │   ├───audits/
    │   ├───billing/
    │   ├───integrations/
    │   ├───notifications/
    │   ├───organizations/
    │   ├───reports/
    │   └───users/
    ├───config/
    │   ├───__init__.py
    │   ├───asgi.py
    │   ├───celery.py
    │   ├───urls.py
    │   ├───wsgi.py
    │   └───settings/
    ├───middleware/
    │   ├───__init__.py
    │   ├───audit_logging.py
    │   └───org_context.py
    ├───requirements/
    │   ├───base.txt
    │   ├───local.txt
    │   └───production.txt
    ├───scripts/
    │   ├───rotate_fernet_keys.py
    │   └───seed_dev_data.py
    ├───services/
    │   ├───__init__.py
    │   ├───ai_service.py
    │   ├───aws_service.py
    │   ├───encryption_manager.py
    │   ├───export_service.py
    │   ├───github_service.py
    │   └───permission_service.py
    ├───static/
    │   └───css/
    │       └───pdf.css
    ├───templates/
    │   ├───base.html
    │   ├───emails/
    │   └───reports/
    └───tests/
        ├───__init__.py
        └───conftest.py
```
