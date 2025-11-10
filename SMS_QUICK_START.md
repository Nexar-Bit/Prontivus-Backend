# SMS Notifications - Quick Start Guide

## ✅ Step 1: Install Twilio (Already Done!)

Twilio has been installed. You can verify with:
```bash
pip show twilio
```

## 📝 Step 2: Get Twilio Credentials

### Option A: Use Twilio Trial Account (Recommended for Testing)

1. **Sign up for free**: https://www.twilio.com/try-twilio
   - Free trial includes $15.50 in credits
   - No credit card required for trial

2. **Get your credentials**:
   - Log in to https://console.twilio.com
   - Your **Account SID** and **Auth Token** are on the dashboard
   - Copy both values

3. **Get a phone number**:
   - Go to **Phone Numbers** → **Manage** → **Buy a number**
   - For trial: Use the free trial number provided
   - Copy the number (format: +1234567890)

### Option B: Use Existing Twilio Account

If you already have a Twilio account:
1. Log in to Twilio Console
2. Get Account SID and Auth Token
3. Use your existing Twilio phone number

## 🔧 Step 3: Add to .env File

Open `backend/.env` and add:

```bash
# SMS Configuration
SMS_PROVIDER=twilio
SMS_TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SMS_TWILIO_AUTH_TOKEN=your_auth_token_here
SMS_TWILIO_FROM_NUMBER=+15551234567
```

**Replace with your actual values!**

## 📱 Step 4: Add Phone Number to Profile

1. Go to `http://localhost:3000/settings`
2. Click on **Perfil** tab
3. Add your phone number in the "Telefone" field
4. Click **Salvar Alterações**

## 🧪 Step 5: Test SMS

1. In Settings page, enable **"Notificações SMS"** toggle
2. Scroll down to **"Testar Notificações SMS"** section
3. Click **"Enviar Teste"** button
4. You should receive a test SMS!

## ⚠️ Important Notes

### Trial Account Limitations:
- Can only send SMS to **verified phone numbers**
- To verify a number: Twilio Console → Phone Numbers → Verified Caller IDs
- Add and verify your phone number there first

### Phone Number Format:
- The system automatically normalizes phone numbers
- Supports: `(11) 98765-4321`, `011 98765-4321`, `+5511987654321`
- All formats will be converted to E.164: `+5511987654321`

### Troubleshooting:

**"SMS service is disabled"**
- Check that all 3 Twilio variables are in `.env`
- Restart backend server after adding credentials

**"Número de telefone não encontrado"**
- Add phone number in Settings → Profile → Telefone
- Save the settings

**"Falha ao enviar SMS de teste"**
- Verify Twilio credentials are correct
- For trial: Verify recipient number in Twilio Console
- Check Twilio Console → Monitor → Logs for errors

## 📚 More Information

See `SMS_SETUP.md` for detailed documentation.

