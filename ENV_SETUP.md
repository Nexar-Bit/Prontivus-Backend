# Environment Variables Setup Guide

## Overview

This guide explains how to configure environment variables for the Prontivus backend.

## Quick Start

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your actual values (see below)

3. **NEVER commit `.env` to version control**

## Required Environment Variables

### Database Configuration

```bash
# Format: postgresql+asyncpg://username:password@host:port/database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/prontivus_clinic
```

**⚠️ CRITICAL**: Never hardcode production database credentials in code. Always use environment variables.

### Security Settings

```bash
# Generate a secure secret key using: python generate_secret_key.py
SECRET_KEY=your-secret-key-change-in-production-generate-using-generate_secret_key.py

# JWT Algorithm
ALGORITHM=HS256

# Token expiration times
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### CORS Settings

```bash
# Comma-separated list of allowed origins
# For production, use your actual frontend domain
BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Environment Configuration

```bash
# Environment: development, staging, or production
ENVIRONMENT=development

# Debug mode (should be False in production)
DEBUG=True
```

## Optional Environment Variables

### Redis Configuration (for caching)

```bash
# Redis connection URL
# If not provided, caching will be disabled
REDIS_URL=redis://localhost:6379/0
```

### Sentry Configuration (for error monitoring)

```bash
# Sentry DSN for error tracking
# Get this from your Sentry project settings
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# Sentry environment
SENTRY_ENVIRONMENT=development
```

### Email Configuration (for notifications)

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@prontivus.com
```

### SMS Configuration (for notifications)

```bash
# SMS Provider (currently supports Twilio)
SMS_PROVIDER=twilio
SMS_TWILIO_ACCOUNT_SID=your_twilio_account_sid
SMS_TWILIO_AUTH_TOKEN=your_twilio_auth_token
SMS_TWILIO_FROM_NUMBER=+1234567890
```

**To get Twilio credentials:**
1. Sign up at https://www.twilio.com (free trial with $15.50 credits)
2. Get Account SID and Auth Token from Twilio Console dashboard
3. Purchase or use a trial phone number
4. See `SMS_SETUP.md` for detailed step-by-step instructions

### Push Notification Configuration (for web push)

```bash
# Generate VAPID keys using: python generate_vapid_keys.py
VAPID_PUBLIC_KEY=your-vapid-public-key
VAPID_PRIVATE_KEY=your-vapid-private-key
VAPID_EMAIL=mailto:noreply@prontivus.com
```

**To generate VAPID keys:**
```bash
cd backend
python generate_vapid_keys.py
```

This will output the keys that you need to add to your `.env` file.

## Production Setup

### Render Deployment

1. Go to your Render dashboard
2. Navigate to your service
3. Go to "Environment" tab
4. Add all required environment variables
5. **Never** add `.env` file to your repository

### Environment-Specific Values

#### Development
```bash
ENVIRONMENT=development
DEBUG=True
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/prontivus_clinic_dev
```

#### Staging
```bash
ENVIRONMENT=staging
DEBUG=False
DATABASE_URL=postgresql+asyncpg://user:password@staging-host:5432/prontivus_clinic_staging
```

#### Production
```bash
ENVIRONMENT=production
DEBUG=False
DATABASE_URL=postgresql+asyncpg://user:password@production-host:5432/prontivus_clinic
SENTRY_DSN=your-production-sentry-dsn
REDIS_URL=redis://production-redis:6379/0
```

## Security Best Practices

1. **Never commit `.env` files** - They are in `.gitignore`
2. **Use strong SECRET_KEY** - Generate using `python generate_secret_key.py`
3. **Rotate credentials regularly** - Especially in production
4. **Use different credentials** - For each environment (dev, staging, prod)
5. **Limit CORS origins** - Only allow trusted domains in production
6. **Use environment variables** - Never hardcode credentials in code

## Verification

After setting up environment variables, verify they are loaded correctly:

```bash
# Check if environment variables are loaded
python -c "from config import settings; print(settings.DATABASE_URL)"
```

## Troubleshooting

### Database Connection Issues

- Verify `DATABASE_URL` format is correct
- Check database credentials
- Ensure database is accessible from your network
- Check firewall rules

### Redis Connection Issues

- Verify `REDIS_URL` is correct
- Check if Redis server is running
- Application will continue without Redis (caching disabled)

### Sentry Not Working

- Verify `SENTRY_DSN` is correct
- Check Sentry project settings
- Application will continue without Sentry (monitoring disabled)

---

**Last Updated**: 2025-01-30

