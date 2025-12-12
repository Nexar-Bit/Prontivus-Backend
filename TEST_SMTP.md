# SMTP Configuration Test

This guide explains how to test your SMTP configuration for the Prontivus system.

## Quick Test Script

A standalone Python script is available to test SMTP configuration: `test_smtp.py`

### Method 1: Using Environment Variables (Recommended)

1. Set your SMTP environment variables:
   ```bash
   export SMTP_HOST=smtp.gmail.com
   export SMTP_PORT=587
   export SMTP_USER=your-email@gmail.com
   export SMTP_PASSWORD=your-app-password
   export TEST_EMAIL=recipient@example.com
   ```

2. Run the test script:
   ```bash
   cd backend
   python test_smtp.py
   ```

### Method 2: Using Command-Line Arguments

```bash
cd backend
python test_smtp.py \
  --host smtp.gmail.com \
  --port 587 \
  --user your-email@gmail.com \
  --password your-app-password \
  --to recipient@example.com
```

### Method 3: Quick Test (Uses Defaults)

```bash
cd backend
python test_smtp.py \
  --user your-email@gmail.com \
  --password your-app-password \
  --to recipient@example.com
```

## Using the API Endpoint

You can also test SMTP through the API endpoint (requires authentication):

**Endpoint:** `POST /api/v1/settings/me/test-email`

**Headers:**
```
Authorization: Bearer <your-jwt-token>
Content-Type: application/json
```

**Response:**
```json
{
  "message": "Email de teste enviado com sucesso",
  "email_sent": true,
  "email_enabled": true,
  "email_address": "your-email@example.com"
}
```

## Common SMTP Providers

### Gmail
- **Host:** `smtp.gmail.com`
- **Port:** `587` (TLS) or `465` (SSL)
- **Note:** Requires "App Password" if 2FA is enabled

### Outlook/Hotmail
- **Host:** `smtp-mail.outlook.com`
- **Port:** `587` (TLS)

### Yahoo
- **Host:** `smtp.mail.yahoo.com`
- **Port:** `587` (TLS) or `465` (SSL)

### Custom SMTP Server
- Use your provider's SMTP settings
- Common ports: `25`, `587` (TLS), `465` (SSL)

## Troubleshooting

### Authentication Error
- Verify `SMTP_USER` and `SMTP_PASSWORD` are correct
- For Gmail: Use an "App Password" instead of your regular password
- Check if 2FA is enabled and requires app-specific password

### Connection Error
- Verify `SMTP_HOST` and `SMTP_PORT` are correct
- Check firewall settings
- Ensure network connectivity to SMTP server
- Try different ports (587 for TLS, 465 for SSL)

### Email Not Received
- Check spam/junk folder
- Verify recipient email address is correct
- Check SMTP server logs for delivery issues
- Some providers may delay or block test emails

## Environment Variables

Set these in your `.env` file or environment:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@prontivus.com
```

## Success Indicators

✅ **Connection Successful:** Script connects to SMTP server  
✅ **Authentication Successful:** Credentials are accepted  
✅ **Email Sent:** Test email is sent successfully  
✅ **Email Received:** You receive the test email in your inbox

If all checks pass, your SMTP configuration is working correctly!

