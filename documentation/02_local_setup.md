# 2. Local Development Setup

This guide will walk you through setting up the AuditEase project for local development.

## 1. Prerequisites

Before you begin, ensure you have the following installed on your system:

*   **Python 3.11**
*   **Docker** and **Docker Compose** (for running PostgreSQL and Redis)
*   **Git**

## 2. Clone the Repository

Start by cloning the project repository to your local machine:

```bash
git clone <repository-url>
cd audit_full_app/audit_ease
```

## 3. Set Up Services (Database and Cache)

The simplest way to get PostgreSQL and Redis running for local development is by using the provided Docker Compose configuration.

From the `audit_ease` directory, run:

```bash
docker-compose up -d
```

This will start two services in the background:
*   A PostgreSQL database container.
*   A Redis container for caching and Celery.

## 4. Create and Configure the Environment

The application uses a `.env` file to manage environment variables. A template is provided in `.env.example`.

**a. Create the `.env` file:**

First, create a `.env.example` file in the `audit_ease` directory with the following content (as it is missing from the repository):

```bash
# audit_ease/.env.example

# General
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=
DATABASE_URL=postgres://audit_user:audit_password@127.0.0.1:5432/audit_db
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
FRONTEND_URL=http://localhost:3000

# Security
ENCRYPTION_KEY=
FERNET_KEY=

# Stripe (optional for most local development)
STRIPE_PUBLISHABLE_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# Allowed Hosts
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:8000
```

**b. Create and populate your `.env` file:**

Copy the example file to `.env`:

```bash
cp .env.example .env
```

Now, you need to generate values for `DJANGO_SECRET_KEY` and `ENCRYPTION_KEY`/`FERNET_KEY`.

*   **Generate `DJANGO_SECRET_KEY`:**
    ```bash
    python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
    ```
    Copy the output and paste it as the value for `DJANGO_SECRET_KEY` in your `.env` file.

*   **Generate `ENCRYPTION_KEY`/`FERNET_KEY`:**
    ```bash
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ```
    Copy the output and use it for both `ENCRYPTION_KEY` and `FERNET_KEY` in your `.env` file.

Leave the other variables as they are for now. The default database URL will work with the Docker Compose setup.

## 5. Set Up a Virtual Environment and Install Dependencies

**a. Create and activate a virtual environment:**

```bash
python3 -m venv ../aud
source ../aud/bin/activate
```

**b. Install the required Python packages:**

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 6. Run Database Migrations

Apply the database schema migrations:

```bash
python manage.py migrate
```

## 7. Create a Superuser (Optional)

To access the Django admin interface, create a superuser:

```bash
python manage.py createsuperuser
```

Follow the prompts to set a username, email, and password.

## 8. Run the Development Server

You are now ready to start the Django development server:

```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000`.

## 9. Run the Celery Worker (Optional)

If you need to test functionality that relies on background tasks (like sending emails or processing integrations), you'll need to run a Celery worker in a separate terminal.

Make sure you have activated the virtual environment in the new terminal first.

```bash
celery -A config.celery_app worker --loglevel=info
```

You now have a fully functional local development environment for AuditEase.
