# AuditEase Features List

This document provides a comprehensive list of all features in the **AuditEase** platform, ranging from core architectural capabilities to specific user-facing functionalities.

---

## 1. 🔐 Core Authentication & User Management
The foundation of the platform, handling user identity and secure access.

*   **Email-Based Registration**: Users sign up using email and password (no usernames required).
*   **JWT Authentication**: Secure, stateless authentication using JSON Web Tokens (Access & Refresh tokens).
*   **Custom User Model**: tailored user schema optimized for B2B SaaS requirements.
*   **User Profile Management**: Endpoints to retrieve user details and context (`/users/me/`).
*   **Context Awareness**: Automatic detection of the active organization context for the logged-in user.

## 2. 🏢 Multi-Tenancy & Team Management (Organizations)
Built for B2B usage, allowing users to collaborate in isolated workspaces.

*   **Organization Creation**: Users can create multiple organizations (tenants).
*   **Tenant Isolation**: Strict logical separation of data; users only access data within their active organization.
*   **Role-Based Access Control (RBAC)**:
    *   **Admin**: Full access, including billing and member management.
    *   **Member**: Can run audits and view results.
    *   **Viewer**: Read-only access to reports and dashboards.
*   **Secure Invitation System**:
    *   Admins can invite new members via email.
    *   Generates secure, time-limited (7-day) 32-byte hex tokens.
    *   Acceptance flow adds users to the organization with assigned roles.
*   **Automated Admin Assignment**: The creator of an organization is automatically assigned the ADMIN role.
*   **Membership Management**: Admins can remove members (with protections against removing the last admin).

## 3. 🛡️ Audit & Compliance Engine
The core value proposition: automated security and compliance checking.

*   **Asynchronous Execution**: Audits run in the background (via Celery & Redis) to prevent blocking the UI.
*   **Audit Lifecycle Management**: Tracks status transitions: `PENDING` → `RUNNING` → `COMPLETED` / `FAILED`.
*   **Evidence Collection**: Granular storage of pass/fail results for every individual check.
*   **Raw Data Capture**: Stores full JSON responses from external APIs for debugging and proof.
*   **Rate Limiting**: Defenses against abuse (default: 5 audits per hour per organization).
*   **Executive Dashboard**: Aggregated metrics including:
    *   Overall Pass Rate %.
    *   Top Failing Resources.
    *   Issues categorized by Severity (Critical, High, Medium, Low).

## 4. 💳 Billing & Monetization (Stripe Integration)
Infrastructure for SaaS revenue generation.

*   **Subscription Management**: Support for tiered plans (Free vs. Pro).
*   **Stripe Checkout Integration**: Seamless redirection to hosted Stripe payment pages.
*   **Automated Webhook Handling**: Real-time processing of Stripe events:
    *   `checkout.session.completed`: Activates subscriptions.
    *   `customer.subscription.deleted`: Downgrades to free tier.
    *   `invoice.payment_failed`: Handles dunning/churn.
*   **Feature Gating**: "Premium-only" locks on specific features (e.g., CSV Export).
*   **Permission Guards**: `HasActiveSubscription` permission class to strictly enforce paywalls at the API level.

## 5. 🔌 Integrations & Security
Secure connectivity with external providers.

*   **Encrypted Credential Storage**: All API keys (GitHub, AWS) are encrypted at rest using **Fernet** (symmetric encryption).
*   **On-the-fly Decryption**: Tokens are decrypted only in memory when needed by workers.
*   **Key Rotation Utility**: Scripts to safely rotate encryption keys (`rotate_fernet_keys.py`).
*   **GitHub Integration**: Fetches repository configurations for compliance checks.
*   **AWS Integration**: Hooks for auditing AWS cloud resources.

## 6. 📊 Reporting & Data Export
Tools for getting data out of the system.

*   **CSV Data Export** (Premium Feature):
    *   Streaming response for handling large datasets efficiently.
    *   Includes Resource ID, Check Name, Status, Severity, and Comments.
*   **PDF Reports** (Foundations): Templates and services structure for generating PDF compliance certificates.
*   **Dashboard Summaries**: Visual breakdown of compliance posture over time (30-day lookback).

## 7. 🔔 Notifications
Keeping users informed.

*   **Email Notifications**: Integration with SendGrid/SMTP for transactional emails.
*   **Invitation Emails**: Automated delivery of secure invite links.
*   **Audit Completion Alerts**: (Configurable) Notifications when long-running audits finish.

## 8. 🏗️ Tech Stack & Infrastructure Features
Under-the-hood capabilities that power the platform.

*   **Modular Monolith Architecture**: Clean separation of concerns (Apps: Users, Orgs, Audits, Billing).
*   **Dockerized Deployment**: Full container support for Web, Worker, DB, and Redis.
*   **PostgreSQL**: Robust relational data storage with ACID compliance.
*   **Redis**: High-performance broker for tasks and caching.
*   **Nginx**: Production-grade reverse proxy configuration.
*   **Environment Configuration**: STRICT separation of secrets using `.env` files.
