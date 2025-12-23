"""
Test SMTP connection and email sending
"""
import asyncio
import os
from dotenv import load_dotenv
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Force reload .env file
load_dotenv(override=True)

async def test_smtp_connection():
    """Test SMTP connection"""
    print("=" * 70)
    print("📧 SMTP Connection Test")
    print("=" * 70)
    print()
    
    # Get SMTP settings - try multiple ways
    smtp_host = os.getenv("SMTP_HOST") or os.environ.get("SMTP_HOST", "smtpout.secureserver.net")
    smtp_port = int(os.getenv("SMTP_PORT") or os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER") or os.environ.get("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD") or os.environ.get("SMTP_PASSWORD", "")
    smtp_from_email = os.getenv("SMTP_FROM_EMAIL") or os.environ.get("SMTP_FROM_EMAIL", "suporte@prontivus.com")
    
    print("📋 SMTP Configuration:")
    print(f"   Host: {smtp_host}")
    print(f"   Port: {smtp_port}")
    print(f"   User: {smtp_user if smtp_user else '(not configured)'}")
    print(f"   From Email: {smtp_from_email}")
    print()
    
    if not smtp_user or not smtp_password:
        print("❌ SMTP credentials not configured!")
        print()
        print("💡 Add to backend/.env file:")
        print("   SMTP_HOST=smtpout.secureserver.net")
        print("   SMTP_PORT=587")
        print("   SMTP_USER=your-email@domain.com")
        print("   SMTP_PASSWORD=your-password")
        print("   SMTP_FROM_EMAIL=suporte@prontivus.com")
        return False
    
    try:
        print("🔌 Testing SMTP connection...")
        
        # Create SSL context
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.minimum_version = ssl.TLSVersion.MINIMUM_SUPPORTED
        context.maximum_version = ssl.TLSVersion.MAXIMUM_SUPPORTED
        
        timeout = 60  # Increased timeout for GoDaddy servers
        
        # Test connection based on port
        if smtp_port == 465 or smtp_port == 3535:
            print(f"   Using SSL connection (port {smtp_port})...")
            try:
                with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=timeout) as server:
                    print("   ✅ SSL connection established")
                    server.login(smtp_user, smtp_password)
                    print("   ✅ Authentication successful")
                    connection_method = "SSL"
            except (ssl.SSLError, OSError) as ssl_error:
                print(f"   ⚠️  SSL connection failed: {ssl_error}")
                print("   Trying TLS instead...")
                with smtplib.SMTP(smtp_host, smtp_port, timeout=timeout) as server:
                    server.starttls(context=context)
                    server.login(smtp_user, smtp_password)
                    print("   ✅ TLS connection and authentication successful")
                    connection_method = "TLS"
        else:
            print(f"   Using TLS connection (port {smtp_port})...")
            with smtplib.SMTP(smtp_host, smtp_port, timeout=timeout) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                print("   ✅ TLS connection established")
                server.login(smtp_user, smtp_password)
                print("   ✅ Authentication successful")
                connection_method = "TLS"
        
        print()
        print("=" * 70)
        print("✅ SMTP Connection Test: SUCCESS")
        print("=" * 70)
        print(f"   Connection: {connection_method}")
        print(f"   Server: {smtp_host}:{smtp_port}")
        print(f"   Authenticated as: {smtp_user}")
        print()
        
        # Ask if user wants to send a test email
        print("💡 Connection test successful!")
        print("   You can now send emails through the Prontivus system.")
        
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print()
        print("=" * 70)
        print("❌ SMTP Authentication Failed")
        print("=" * 70)
        print(f"   Error: {str(e)}")
        print()
        print("💡 Troubleshooting:")
        print("   1. Verify SMTP_USER and SMTP_PASSWORD are correct")
        print("   2. Check if your email account requires app-specific passwords")
        print("   3. Ensure 2FA is configured correctly for SMTP access")
        print("   4. For GoDaddy/SecureServer, verify credentials in cPanel")
        return False
        
    except smtplib.SMTPConnectError as e:
        print()
        print("=" * 70)
        print("❌ SMTP Connection Failed")
        print("=" * 70)
        print(f"   Error: {str(e)}")
        print()
        print("💡 Troubleshooting:")
        print("   1. Check SMTP_HOST and SMTP_PORT are correct")
        print("   2. Verify firewall/network allows outbound SMTP connections")
        print("   3. Check if your ISP blocks port 587/465")
        print("   4. Try alternative ports: 25, 465, 587, 3535")
        return False
        
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ SMTP Test Failed")
        print("=" * 70)
        print(f"   Error: {str(e)}")
        print()
        print("💡 Common issues:")
        print("   1. Incorrect SMTP settings")
        print("   2. Network/firewall blocking connection")
        print("   3. SSL/TLS configuration issues")
        print("   4. Server temporarily unavailable")
        import traceback
        traceback.print_exc()
        return False

async def send_test_email():
    """Send a test email"""
    print()
    print("=" * 70)
    print("📧 Send Test Email")
    print("=" * 70)
    print()
    
    smtp_host = os.getenv("SMTP_HOST", "smtpout.secureserver.net")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from_email = os.getenv("SMTP_FROM_EMAIL", "suporte@prontivus.com")
    
    if not smtp_user or not smtp_password:
        print("❌ SMTP not configured")
        return False
    
    # Get test email address
    test_email = input("Enter test email address (or press Enter to skip): ").strip()
    if not test_email:
        print("⏭️  Skipping test email")
        return True
    
    try:
        # Create test message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Prontivus - SMTP Test Email"
        msg['From'] = smtp_from_email
        msg['To'] = test_email
        
        html_body = f"""
        <html>
        <body>
            <h2>✅ SMTP Test Successful!</h2>
            <p>This is a test email from Prontivus Healthcare Management System.</p>
            <p><strong>Test Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>If you received this email, your SMTP configuration is working correctly.</p>
            <hr>
            <p style="color: #666; font-size: 12px;">This is an automated test message.</p>
        </body>
        </html>
        """
        
        text_body = f"""
Prontivus - SMTP Test Email

This is a test email from Prontivus Healthcare Management System.

Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

If you received this email, your SMTP configuration is working correctly.
        """
        
        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send email
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        print(f"📤 Sending test email to {test_email}...")
        
        if smtp_port == 465 or smtp_port == 3535:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=30) as server:
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        
        print("✅ Test email sent successfully!")
        print(f"   Check inbox at: {test_email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send test email: {str(e)}")
        return False

async def main():
    """Main test function"""
    # Test connection
    success = await test_smtp_connection()
    
    if success:
        # Optionally send test email
        await send_test_email()
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)

