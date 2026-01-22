# 1. Project Overview

AuditEase is a production-ready B2B SaaS platform for security auditing. It allows users to work in teams, manage organizations, and perform security audits. The platform supports different subscription tiers (Free and Premium) with feature gating.

## Core Features

*   **Organizations and Teams:** The application is multi-tenant, with data isolated between organizations. Users can be members of multiple organizations with different roles (Admin, Member, Viewer). Team members can be invited via secure tokens.
*   **Billing and Subscriptions:** Integrated with Stripe for handling subscriptions. Organizations can upgrade to a premium plan to access premium features. The subscription lifecycle is managed automatically via Stripe webhooks.
*   **Security Auditing:** Users can initiate security audits and view the results.
*   **Data Portability:** Premium users can export audit data as a CSV file.
*   **Role-Based Access Control (RBAC):** Access to features and data is controlled by a set of permission classes, ensuring that users can only access what they are authorized to.

## Technology Stack

*   **Backend:** Django, Django REST Framework
*   **Database:** SQLite (for development), PostgreSQL (recommended for production)
*   **Asynchronous Tasks:** Celery with Redis or RabbitMQ
*   **Payments:** Stripe
*   **Containerization:** Docker, Docker Compose

## Project Structure

The project is organized into several Django apps:

*   `apps/audits`: Core auditing functionality.
*   `apps/billing`: Stripe integration and subscription management.
*   `apps/integrations`: For third-party integrations (e.g., GitHub).
*   `apps/notifications`: Handles user notifications.
*   `apps/organizations`: Manages organizations, memberships, and invitations.
*   `apps/reports`: For generating and viewing reports.
*   `apps/users`: User authentication and management.

This documentation will guide you through setting up the project for local development, deploying it to production, and understanding its architecture and APIs in detail.
