"""
Test SMS Service
Quick test script to verify Twilio SMS integration
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_sms_service():
    """Test the SMS service"""
    from app.services.sms_service import sms_service
    
    print("=" * 60)
    print("SMS Service Test")
    print("=" * 60)
    
    # Check if SMS service is enabled
    print(f"\n1. SMS Service Status:")
    print(f"   Enabled: {sms_service.is_enabled()}")
    print(f"   Provider: {sms_service.provider}")
    
    if not sms_service.is_enabled():
        print("\n[ERROR] SMS service is disabled!")
        print("\nChecking environment variables:")
        print(f"   SMS_PROVIDER: {os.getenv('SMS_PROVIDER', 'NOT SET')}")
        print(f"   SMS_TWILIO_ACCOUNT_SID: {os.getenv('SMS_TWILIO_ACCOUNT_SID', 'NOT SET')[:20]}...")
        print(f"   SMS_TWILIO_AUTH_TOKEN: {'SET' if os.getenv('SMS_TWILIO_AUTH_TOKEN') else 'NOT SET'}")
        print(f"   SMS_TWILIO_FROM_NUMBER: {os.getenv('SMS_TWILIO_FROM_NUMBER', 'NOT SET')}")
        return False
    
    print(f"   Account SID: {sms_service.twilio_account_sid[:20]}...")
    print(f"   From Number: {sms_service.twilio_from_number}")
    
    # Test phone number normalization
    print(f"\n2. Phone Number Normalization Test:")
    test_numbers = [
        "+5511999999999",
        "11999999999",
        "(11) 99999-9999",
        "5511999999999"
    ]
    for number in test_numbers:
        normalized = sms_service.normalize_phone_number(number)
        print(f"   {number:20} -> {normalized}")
    
    # Get test phone number from command line or skip
    print(f"\n3. Send Test SMS:")
    if len(sys.argv) > 1:
        test_phone = sys.argv[1].strip()
        print(f"   Using phone number from command line: {test_phone}")
    else:
        print("   No phone number provided. Usage: python test_sms.py <phone_number>")
        print("   Example: python test_sms.py +5511999999999")
        return True
    
    # Normalize the test phone number
    normalized_phone = sms_service.normalize_phone_number(test_phone)
    print(f"   Normalized phone: {normalized_phone}")
    
    # Send test SMS
    print(f"\n   Sending test SMS to {normalized_phone}...")
    try:
        success = await sms_service.send_notification_sms(
            to_phone=normalized_phone,
            notification_title="Teste de SMS",
            notification_message="Este é um SMS de teste do sistema Prontivus. Se você recebeu esta mensagem, o serviço SMS está funcionando corretamente!"
        )
        
        if success:
            print(f"\n[SUCCESS] SMS sent successfully!")
            print(f"   Check your phone for the message.")
            return True
        else:
            print(f"\n[FAILED] Failed to send SMS")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Error sending SMS: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_sms_service())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
