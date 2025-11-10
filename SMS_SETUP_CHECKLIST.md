# SMS Notifications Setup Checklist

## ✅ Completed Steps

- [x] Twilio library installed (version 9.8.5)
- [x] SMS service created (`backend/app/services/sms_service.py`)
- [x] API endpoint created (`POST /api/settings/me/test-sms`)
- [x] Frontend integration complete
- [x] Documentation created

## 📋 Next Steps (Do These Now)

### Step 1: Get Twilio Account (5 minutes)

1. Go to https://www.twilio.com/try-twilio
2. Sign up with your email
3. Verify your email address
4. Verify your phone number (for trial account)

### Step 2: Get Twilio Credentials (2 minutes)

1. Log in to https://console.twilio.com
2. On the dashboard, you'll see:
   - **Account SID** (starts with `AC...`)
   - **Auth Token** (click "show" to reveal)
3. Copy both values

### Step 3: Get Twilio Phone Number (2 minutes)

1. In Twilio Console, go to **Phone Numbers** → **Manage** → **Buy a number**
2. For trial: You'll see a free trial number, or click "Get a number"
3. Select a number (US numbers are free for trial)
4. Copy the number (format: `+1234567890`)

### Step 4: Add Credentials to .env (1 minute)

Open `backend/.env` file and add:

```bash
SMS_PROVIDER=twilio
SMS_TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SMS_TWILIO_AUTH_TOKEN=your_auth_token_here
SMS_TWILIO_FROM_NUMBER=+15551234567
```

**Replace with your actual values!**

### Step 5: Restart Backend Server

Stop and restart your FastAPI server to load the new environment variables.

### Step 6: Add Phone Number to Profile (2 minutes)

1. Open `http://localhost:3000/settings`
2. Click the **"Perfil"** tab
3. Find the **"Telefone"** field
4. Enter your phone number (any format works):
   - `(11) 98765-4321`
   - `011 98765-4321`
   - `+5511987654321`
5. Click **"Salvar Alterações"** button

### Step 7: Test SMS Notifications (1 minute)

1. In Settings page, scroll to **"Canais de Notificação"**
2. Enable the **"Notificações SMS"** toggle
3. Scroll down to **"Testar Notificações SMS"** section
4. Click **"Enviar Teste"** button
5. Check your phone for the test SMS!

## 🎉 Expected Result

After completing all steps, you should:
- See "SMS de teste enviado para +5511987654321" success message
- Receive a test SMS on your phone with message:
  ```
  Prontivus: Teste de Notificação SMS
  
  Este é um SMS de teste do sistema Prontivus. Se você recebeu esta mensagem, suas configurações de notificação SMS estão funcionando corretamente.
  
  - Sistema Prontivus
  ```

## ⚠️ Troubleshooting

### If you see "SMS service is disabled":
- Check that all 3 Twilio variables are in `.env`
- Make sure there are no typos
- Restart backend server

### If you see "Número de telefone não encontrado":
- Add phone number in Settings → Profile
- Make sure you clicked "Salvar Alterações"

### If you see "Falha ao enviar SMS de teste":
- Verify Twilio credentials are correct
- For trial accounts: Verify your phone number in Twilio Console
- Check Twilio Console → Monitor → Logs for error details

### If SMS not received:
- Check Twilio Console → Monitor → Logs
- For trial: Make sure recipient number is verified in Twilio
- Check phone spam folder
- Verify phone number format is correct

## 📞 Need Help?

- See `SMS_SETUP.md` for detailed documentation
- See `SMS_QUICK_START.md` for quick reference
- Check Twilio Console logs for error messages

