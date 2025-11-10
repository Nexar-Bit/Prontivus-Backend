# SMS Notifications Setup Guide

## Overview

This guide explains how to configure SMS notifications using Twilio in the Prontivus system.

## Prerequisites

- Twilio account (sign up at https://www.twilio.com)
- Twilio Account SID and Auth Token
- A Twilio phone number (can use trial number for testing)

## Step 1: Create Twilio Account

1. Go to https://www.twilio.com/try-twilio
2. Sign up for a free account
3. Verify your email and phone number
4. You'll get a trial account with $15.50 in credits

## Step 2: Get Twilio Credentials

1. Log in to your Twilio Console: https://console.twilio.com
2. Your **Account SID** and **Auth Token** are displayed on the dashboard
3. Copy these values (keep them secure!)

## Step 3: Get a Twilio Phone Number

1. In Twilio Console, go to **Phone Numbers** → **Manage** → **Buy a number**
2. For testing, you can use a trial number (free)
3. For production, purchase a number in your target country
4. Copy the phone number (format: +1234567890)

## Step 4: Configure Environment Variables

Add these to your `backend/.env` file:

```bash
# SMS Configuration
SMS_PROVIDER=twilio
SMS_TWILIO_ACCOUNT_SID=your_account_sid_here
SMS_TWILIO_AUTH_TOKEN=your_auth_token_here
SMS_TWILIO_FROM_NUMBER=+1234567890
```

**Example (with placeholder values):**
```bash
SMS_PROVIDER=twilio
SMS_TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SMS_TWILIO_AUTH_TOKEN=your_auth_token_here
SMS_TWILIO_FROM_NUMBER=+15551234567
```

**Note:** Replace `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` with your actual Twilio Account SID from the Twilio Console.

## Step 5: Add Phone Number to User Profile

1. Users must add their phone number in Settings → Profile
2. Phone number will be automatically normalized to E.164 format
3. Supports Brazilian and international formats

## Step 6: Test SMS Notifications

1. Go to `http://localhost:3000/settings`
2. Enable "Notificações SMS" toggle
3. Make sure you have a phone number in your profile
4. Click "Enviar Teste" under "Testar Notificações SMS"
5. You should receive a test SMS

## Phone Number Formats Supported

The system automatically normalizes:
- Brazilian: `(11) 98765-4321` → `+5511987654321`
- Brazilian with 0: `011 98765-4321` → `+5511987654321`
- International: `+1 555 123 4567` → `+15551234567`
- E.164: `+5511987654321` → `+5511987654321`

## Twilio Trial Limitations

- Can only send SMS to verified phone numbers
- To test, verify your phone number in Twilio Console
- For production, upgrade your Twilio account

## Troubleshooting

### "SMS service is disabled"
- Check that all Twilio credentials are set in `.env`
- Restart the backend server after adding credentials

### "Número de telefone não encontrado"
- Add a phone number in Settings → Profile
- Make sure the phone number is saved

### "Falha ao enviar SMS de teste"
- Verify Twilio credentials are correct
- Check that your Twilio account has credits
- For trial accounts, verify the recipient phone number in Twilio Console
- Check Twilio logs in the Twilio Console for error details

### SMS not received
- Check spam folder (some carriers filter SMS)
- Verify phone number format is correct
- For trial accounts, ensure recipient number is verified in Twilio
- Check Twilio Console → Monitor → Logs for delivery status

## Cost Information

- Twilio pricing: ~$0.0075 per SMS in US, varies by country
- Trial account: $15.50 free credits
- Monitor usage in Twilio Console

## Security Notes

⚠️ **IMPORTANT:**
- Never commit `.env` file to version control
- Keep Twilio Auth Token secure
- Rotate credentials regularly in production
- Use environment variables, never hardcode credentials

## Next Steps

After setup:
1. Test SMS notifications from settings page
2. Integrate SMS into your notification workflows
3. Monitor SMS usage and costs in Twilio Console
4. Set up alerts for low balance in Twilio

