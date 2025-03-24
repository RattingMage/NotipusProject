# Notipus

A project for Slack authentication with Stripe integration for subscription management.

## Key Features

- User authentication via Slack OAuth
- Stripe integration for subscription management
- Feature restrictions based on subscription plans

## Tech Stack

- Python 3.13
- Django 5.0+
- Django Ninja (for API)
- Stripe API
- Slack API
- PostgreSQL

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/RattingMage/NotipusProject.git
cd NotipusProject
```

### 2. Set up Poetry for dependency management:

```bash
poetry install
```

### 3. Configure environment variables

```markdown
# Django
SECRET_KEY=...
DEBUG=True
ALLOWED_HOSTS=localhost, 127.0.0.1

# Database
DB_NAME=app_db
DB_USER=app_user
DB_PASSWORD=secure_password
DB_HOST=localhost

# Slack
SLACK_CLIENT_ID=your_slack_client_id
SLACK_CLIENT_SECRET=your_slack_secret
SLACK_REDIRECT_URI=https://yourdomain.com/auth/slack/callback/

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_12345
STRIPE_SUCCESS_URL = https://{app_domain}/integration/success/
STRIPE_CANCEL_URL = https://{app_domain}/integration/cancel/
```

### 4. Apply migrations

```bash
poetry run python manage.py migrate 
```

### 5. Run the server

```bash
poetry run python manage.py runserver 
```

## API Endpoints

### Authentication
`GET` `/api/auth/slack/` - Initiate Slack authentication

`GET` `/api/auth/slack/callback/` - Callback URL for Slack OAuth

### Integrations
`POST` `/api/integration/stripe/connect/` - Connect Stripe

`GET` `/api/integration/stripe/status/` - Check Stripe status

### Webhooks
`POST` `/api/webhook/stripe/` - Stripe webhook

`GET` `/api/webhook/health_check/` - API health check