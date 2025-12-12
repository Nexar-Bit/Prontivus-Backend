#!/usr/bin/env python3
"""
SMTP Configuration Test Script
Tests SMTP connection and sends a test email
"""
import os
import sys
import smtplib
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def test_smtp_connection(
    smtp_host: str = None,
    smtp_port: int = None,
    smtp_user: str = None,
    smtp_password: str = None,
    smtp_from_email: str = None,
    test_email: str = None
):
    """Test SMTP connection and send a test email"""
    
    # Get SMTP configuration from arguments or environment variables
    smtp_host = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
    smtp_user = smtp_user or os.getenv("SMTP_USER", "")
    smtp_password = smtp_password or os.getenv("SMTP_PASSWORD", "")
    smtp_from_email = smtp_from_email or os.getenv("SMTP_FROM_EMAIL", smtp_user or "noreply@prontivus.com")
    
    # Test email recipient (can be overridden with TEST_EMAIL env var or argument)
    test_email = test_email or os.getenv("TEST_EMAIL", smtp_user)
    
    print("=" * 60)
    print("SMTP Configuration Test")
    print("=" * 60)
    print(f"SMTP Host: {smtp_host}")
    print(f"SMTP Port: {smtp_port}")
    print(f"SMTP User: {smtp_user}")
    print(f"SMTP From Email: {smtp_from_email}")
    print(f"Test Email Recipient: {test_email}")
    print("=" * 60)
    print()
    
    # Validate configuration
    if not smtp_user:
        print("❌ ERROR: SMTP_USER environment variable is not set")
        return False
    
    if not smtp_password:
        print("❌ ERROR: SMTP_PASSWORD environment variable is not set")
        return False
    
    if not test_email:
        print("❌ ERROR: No test email recipient specified (set TEST_EMAIL env var)")
        return False
    
    try:
        print(f"🔌 Attempting to connect to {smtp_host}:{smtp_port}...")
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Prontivus - Teste de Configuração SMTP - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        msg['From'] = smtp_from_email
        msg['To'] = test_email
        
        # Create email content
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #0F4C75; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 30px; border: 1px solid #ddd; }}
                .success {{ background-color: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin: 20px 0; }}
                .info {{ background-color: #e7f3ff; border-left: 4px solid #2196F3; padding: 15px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ Teste de Configuração SMTP</h1>
                </div>
                <div class="content">
                    <div class="success">
                        <strong>Sucesso!</strong> A configuração SMTP do Prontivus está funcionando corretamente.
                    </div>
                    <div class="info">
                        <strong>Detalhes da Configuração:</strong><br>
                        <ul>
                            <li><strong>Servidor SMTP:</strong> {smtp_host}</li>
                            <li><strong>Porta:</strong> {smtp_port}</li>
                            <li><strong>Usuário:</strong> {smtp_user}</li>
                            <li><strong>Email Remetente:</strong> {smtp_from_email}</li>
                            <li><strong>Data/Hora do Teste:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</li>
                        </ul>
                    </div>
                    <p>Se você recebeu este email, significa que:</p>
                    <ul>
                        <li>✅ A conexão com o servidor SMTP foi estabelecida com sucesso</li>
                        <li>✅ As credenciais de autenticação estão corretas</li>
                        <li>✅ O servidor SMTP aceitou e processou o email</li>
                        <li>✅ O sistema está pronto para enviar emails de notificação</li>
                    </ul>
                </div>
                <div class="footer">
                    <p>Este é um email de teste automático do sistema Prontivus.</p>
                    <p>Se você não esperava receber este email, pode ignorá-lo com segurança.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
Prontivus - Teste de Configuração SMTP

✅ SUCESSO! A configuração SMTP do Prontivus está funcionando corretamente.

Detalhes da Configuração:
- Servidor SMTP: {smtp_host}
- Porta: {smtp_port}
- Usuário: {smtp_user}
- Email Remetente: {smtp_from_email}
- Data/Hora do Teste: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

Se você recebeu este email, significa que:
✅ A conexão com o servidor SMTP foi estabelecida com sucesso
✅ As credenciais de autenticação estão corretas
✅ O servidor SMTP aceitou e processou o email
✅ O sistema está pronto para enviar emails de notificação

---
Este é um email de teste automático do sistema Prontivus.
Se você não esperava receber este email, pode ignorá-lo com segurança.
        """
        
        # Add text and HTML parts
        text_part = MIMEText(text_body, 'plain', 'utf-8')
        msg.attach(text_part)
        
        html_part = MIMEText(html_body, 'html', 'utf-8')
        msg.attach(html_part)
        
        # Connect and send email
        print(f"🔐 Authenticating with SMTP server...")
        
        if smtp_port == 465:
            # Use SSL for port 465 with proper SSL context
            print(f"📧 Using SSL connection (port 465)...")
            import ssl
            # Create a default SSL context that's more permissive
            context = ssl.create_default_context()
            # Some servers require less strict SSL verification
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            # Try different SSL/TLS versions for compatibility
            context.minimum_version = ssl.TLSVersion.MINIMUM_SUPPORTED
            context.maximum_version = ssl.TLSVersion.MAXIMUM_SUPPORTED
            
            try:
                # Try with longer timeout for GoDaddy servers
                with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=60) as server:
                    # Set debug level to see what's happening
                    # server.set_debuglevel(1)
                    server.login(smtp_user, smtp_password)
                    print(f"✅ Authentication successful!")
                    print(f"📤 Sending test email to {test_email}...")
                    server.send_message(msg)
            except (ConnectionResetError, OSError, socket.timeout) as e:
                print(f"⚠️  SSL connection failed: {str(e)}")
                print(f"⚠️  Trying alternative port 80 (GoDaddy sometimes uses this)...")
                # Try alternative: port 80 (GoDaddy sometimes uses this)
                try:
                    smtp_port_alt = 80
                    with smtplib.SMTP(smtp_host, smtp_port_alt, timeout=60) as server:
                        server.starttls(context=context)
                        server.login(smtp_user, smtp_password)
                        print(f"✅ Authentication successful on port 80!")
                        print(f"📤 Sending test email to {test_email}...")
                        server.send_message(msg)
                except Exception as e2:
                    print(f"⚠️  Port 80 also failed, trying port 587 with TLS...")
                    # Try alternative: port 587 with TLS
                    smtp_port_alt = 587
                    with smtplib.SMTP(smtp_host, smtp_port_alt, timeout=60) as server:
                        server.starttls(context=context)
                        server.login(smtp_user, smtp_password)
                        print(f"✅ Authentication successful on port 587!")
                        print(f"📤 Sending test email to {test_email}...")
                        server.send_message(msg)
        else:
            # Use TLS for port 587 and others
            print(f"📧 Using TLS connection (port {smtp_port})...")
            import ssl
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                server.starttls(context=context)
                server.login(smtp_user, smtp_password)
                print(f"✅ Authentication successful!")
                print(f"📤 Sending test email to {test_email}...")
                server.send_message(msg)
        
        print()
        print("=" * 60)
        print("✅ SUCCESS! Test email sent successfully!")
        print("=" * 60)
        print(f"📬 Check the inbox of: {test_email}")
        print(f"📧 Subject: {msg['Subject']}")
        print()
        print("If you received the email, your SMTP configuration is working correctly!")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print()
        print("=" * 60)
        print("❌ AUTHENTICATION ERROR")
        print("=" * 60)
        print(f"Failed to authenticate with SMTP server.")
        print(f"Error: {str(e)}")
        print()
        print("Possible causes:")
        print("  - Incorrect SMTP_USER or SMTP_PASSWORD")
        print("  - Account requires 'App Password' (for Gmail, enable 2FA and generate app password)")
        print("  - Account is locked or disabled")
        print("  - SMTP server requires different authentication method")
        return False
        
    except smtplib.SMTPConnectError as e:
        print()
        print("=" * 60)
        print("❌ CONNECTION ERROR")
        print("=" * 60)
        print(f"Failed to connect to SMTP server: {smtp_host}:{smtp_port}")
        print(f"Error: {str(e)}")
        print()
        print("Possible causes:")
        print("  - Incorrect SMTP_HOST or SMTP_PORT")
        print("  - Firewall blocking the connection")
        print("  - SMTP server is down or unreachable")
        print("  - Network connectivity issues")
        return False
        
    except smtplib.SMTPException as e:
        print()
        print("=" * 60)
        print("❌ SMTP ERROR")
        print("=" * 60)
        print(f"SMTP server returned an error: {str(e)}")
        print()
        print("Possible causes:")
        print("  - Server rejected the email")
        print("  - Invalid sender email address")
        print("  - Server rate limiting")
        print("  - Server configuration issue")
        return False
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ UNEXPECTED ERROR")
        print("=" * 60)
        print(f"An unexpected error occurred: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test SMTP configuration for Prontivus",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using environment variables (recommended)
  export SMTP_HOST=smtp.gmail.com
  export SMTP_PORT=587
  export SMTP_USER=your-email@gmail.com
  export SMTP_PASSWORD=your-app-password
  export TEST_EMAIL=recipient@example.com
  python test_smtp.py

  # Using command-line arguments
  python test_smtp.py --host smtp.gmail.com --port 587 --user your-email@gmail.com --password your-password --to recipient@example.com

  # Quick test with minimal arguments (uses defaults for host/port)
  python test_smtp.py --user your-email@gmail.com --password your-password --to recipient@example.com
        """
    )
    
    parser.add_argument("--host", help="SMTP host (default: smtp.gmail.com)", default=None)
    parser.add_argument("--port", type=int, help="SMTP port (default: 587)", default=None)
    parser.add_argument("--user", help="SMTP username/email", default=None)
    parser.add_argument("--password", help="SMTP password", default=None)
    parser.add_argument("--from-email", help="From email address (default: same as user)", default=None)
    parser.add_argument("--to", help="Test email recipient (default: same as user)", default=None)
    
    args = parser.parse_args()
    
    print()
    success = test_smtp_connection(
        smtp_host=args.host,
        smtp_port=args.port,
        smtp_user=args.user,
        smtp_password=args.password,
        smtp_from_email=args.from_email,
        test_email=args.to
    )
    print()
    sys.exit(0 if success else 1)

