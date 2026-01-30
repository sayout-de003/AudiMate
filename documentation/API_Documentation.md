# API Documentation

## 1. Overview
The AuditMate API is fully documented using **OpenAPI 3.0** (formerly Swagger). 
The documentation is automatically generated from the Django REST Framework serializers and views using `drf-spectacular`.

## 2. Interactive Documentation

We provide two interactive UI options to explore and test the API directly from your browser.

### Swagger UI
*   **URL**: [`/api/docs/`](http://localhost:8000/api/docs/)
*   **Best for**: Developers wanting to "Try it out".
*   **Features**:
    *   Interactive Request/Response builder.
    *   One-click Authentication (Authorize button).
    *   Schema definitions.

### ReDoc
*   **URL**: [`/api/redoc/`](http://localhost:8000/api/redoc/)
*   **Best for**: Reading and navigating complex schemas.
*   **Features**:
    *   Clean, three-panel layout.
    *   Better readability for nested objects.

### Raw JSON Schema
*   **URL**: [`/api/schema/`](http://localhost:8000/api/schema/)
*   **Format**: JSON (OpenAPI 3.0 spec).
*   **Usage**: Import into Postman, Insomnia, or generate client SDKs.

## 3. Authentication
The API uses **JWT (JSON Web Token)** authentication. 

### How to Authenticate in Swagger UI
1.  Click the **Authorize** button at the top right.
2.  Value Format: `Bearer <your_access_token>`
3.  Click **Authorize** to save the token.

### Getting a Token
Use the `POST /api/v1/auth/login/` endpoint with your credentials:
```json
{
  "email": "admin@example.com",
  "password": "yourpassword"
}
```
Response:
```json
{
  "access": "eyJ0eX...",
  "refresh": "eyJ0eX..."
}
```

## 4. Key Endpoints

| Resource | Path | Description |
| :--- | :--- | :--- |
| **Audits** | `/api/v1/audits/` | List, create, and retrieve audits. |
| **Organizations** | `/api/v1/organizations/` | Manage tenants and settings. |
| **Members** | `/api/v1/organizations/{id}/members/` | Manage team access. |
| **Integrations** | `/api/v1/integrations/` | Connect GitHub/Stripe users. |
| **Billing** | `/api/v1/billing/` | Checkout sessions and webhooks. |

## 5. Development
To regenerate the schema manually (e.g., for checking changes without running the server):
```bash
python manage.py spectacular --file schema.yaml
```
