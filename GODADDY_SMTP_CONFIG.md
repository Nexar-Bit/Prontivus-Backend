# GoDaddy SMTP Configuration Analysis

## SMTP Server Information

Based on the GoDaddy email server configuration:

### Outgoing Server (SMTP)
- **Host:** `smtpout.secureserver.net`
- **Available Ports:**
  - **465** (SSL) - Recommended for secure connections
  - **587** (TLS/SSL) - Recommended for Mac and modern clients
  - **25** (Standard SMTP) - May be blocked by some ISPs
  - **80** (HTTP port, rarely used for SMTP)
  - **3535** (Alternative port with SSL)

### Email Account Settings
- **Username:** Your full email address (e.g., `suporte@prontivus.com`)
- **Password:** Your email account password
- **Incoming Server:** 
  - IMAP: `imap.secureserver.net` (port 143 or 993 with SSL)
  - POP: `pop.secureserver.net` (port 110 or 995 with SSL)

## Recommended Configuration for Prontivus

### Environment Variables
```bash
SMTP_HOST=smtpout.secureserver.net
SMTP_PORT=465
SMTP_USER=suporte@prontivus.com
SMTP_PASSWORD=your-email-password
SMTP_FROM_EMAIL=suporte@prontivus.com
```

### Alternative Ports (if 465 doesn't work)
1. **Port 587 (TLS)** - Most compatible, works on Mac and Windows
   ```bash
   SMTP_PORT=587
   ```

2. **Port 3535 (SSL)** - Alternative if 465 is blocked
   ```bash
   SMTP_PORT=3535
   ```

3. **Port 25** - Standard SMTP (may be blocked by ISPs)
   ```bash
   SMTP_PORT=25
   ```

## Current Email Service Support

The Prontivus email service (`backend/app/services/email_service.py`) already supports:
- ✅ **Port 465 (SSL)** - Uses `SMTP_SSL` with SSL context
- ✅ **Port 587 (TLS)** - Uses `SMTP` with `starttls()`
- ✅ **Flexible SSL/TLS** - Handles various certificate requirements
- ✅ **Timeout handling** - 60-second timeout for slow connections
- ✅ **GoDaddy compatibility** - SSL context configured for GoDaddy servers

## Testing the Configuration

### 1. Test with Port 465 (SSL)
```bash
cd backend
python test_smtp.py \
  --host smtpout.secureserver.net \
  --port 465 \
  --user suporte@prontivus.com \
  --password your-password \
  --to recipient@example.com
```

### 2. Test with Port 587 (TLS)
```bash
python test_smtp.py \
  --host smtpout.secureserver.net \
  --port 587 \
  --user suporte@prontivus.com \
  --password your-password \
  --to recipient@example.com
```

### 3. Test with Port 3535 (Alternative SSL)
```bash
python test_smtp.py \
  --host smtpout.secureserver.net \
  --port 3535 \
  --user suporte@prontivus.com \
  --password your-password \
  --to recipient@example.com
```

## Troubleshooting

### If Port 465 Fails:
1. Try port **587** (TLS) - Most reliable for GoDaddy
2. Try port **3535** (Alternative SSL)
3. Check firewall settings - Some networks block port 465

### Common Issues:
- **Authentication Failed:** Verify email and password are correct
- **Connection Timeout:** Try port 587 instead of 465
- **SSL Error:** The service already handles this with flexible SSL context
- **Port Blocked:** Some ISPs block port 25, use 587 or 465

## Best Practice Recommendation

**Use Port 587 (TLS)** for maximum compatibility:
- Works on all platforms (Windows, Mac, Linux)
- Less likely to be blocked by firewalls
- Standard TLS encryption
- Supported by all modern email clients

## Configuration Steps

1. **Set Environment Variables:**
   ```bash
   export SMTP_HOST=smtpout.secureserver.net
   export SMTP_PORT=587
   export SMTP_USER=suporte@prontivus.com
   export SMTP_PASSWORD=your-email-password
   export SMTP_FROM_EMAIL=suporte@prontivus.com
   ```

2. **Test the Configuration:**
   ```bash
   python test_smtp.py
   ```

3. **If Test Succeeds:**
   - Restart the backend server
   - The email service will automatically use these settings

## Notes

- The email service automatically detects port 465 and uses SSL
- For other ports (587, 3535, etc.), it uses TLS with `starttls()`
- SSL context is configured to work with GoDaddy's certificate requirements
- Timeout is set to 60 seconds to handle slower connections

