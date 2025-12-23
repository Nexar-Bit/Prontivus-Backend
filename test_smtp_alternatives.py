"""
Test SMTP with alternative ports and configurations
"""
import smtplib
import ssl
import os
from dotenv import load_dotenv

load_dotenv(override=True)

smtp_host = os.getenv("SMTP_HOST", "smtpout.secureserver.net")
smtp_user = os.getenv("SMTP_USER", "")
smtp_password = os.getenv("SMTP_PASSWORD", "")

if not smtp_user or not smtp_password:
    print("❌ SMTP credentials not configured")
    exit(1)

# Alternative ports to try
ports_to_test = [
    (587, "TLS"),
    (465, "SSL"),
    (3535, "SSL"),
    (25, "Plain/TLS"),
    (80, "HTTP Tunnel"),
]

print("=" * 70)
print("🔍 Testing SMTP Connection - Alternative Ports")
print("=" * 70)
print(f"Host: {smtp_host}")
print(f"User: {smtp_user}")
print()

context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

successful_port = None

for port, method in ports_to_test:
    print(f"Testing port {port} ({method})...", end=" ")
    try:
        if port == 465 or port == 3535:
            # SSL connection
            with smtplib.SMTP_SSL(smtp_host, port, context=context, timeout=30) as server:
                server.login(smtp_user, smtp_password)
                print("✅ SUCCESS")
                successful_port = (port, method)
                break
        else:
            # TLS connection
            with smtplib.SMTP(smtp_host, port, timeout=30) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(smtp_user, smtp_password)
                print("✅ SUCCESS")
                successful_port = (port, method)
                break
    except smtplib.SMTPAuthenticationError:
        print("❌ Authentication failed (wrong credentials)")
    except (smtplib.SMTPConnectError, ConnectionRefusedError, TimeoutError) as e:
        print(f"❌ Connection failed: {type(e).__name__}")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}")

print()
if successful_port:
    port, method = successful_port
    print("=" * 70)
    print("✅ SMTP Connection Successful!")
    print("=" * 70)
    print(f"   Working Port: {port}")
    print(f"   Method: {method}")
    print()
    print(f"💡 Update your .env file:")
    print(f"   SMTP_PORT={port}")
else:
    print("=" * 70)
    print("❌ All Port Tests Failed")
    print("=" * 70)
    print()
    print("💡 Troubleshooting:")
    print("   1. Check firewall allows outbound SMTP (ports 25, 465, 587)")
    print("   2. Verify SMTP credentials are correct")
    print("   3. Check if your ISP blocks SMTP ports")
    print("   4. Try from a different network")
    print("   5. Contact GoDaddy support for SMTP settings")

