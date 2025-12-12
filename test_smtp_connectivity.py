#!/usr/bin/env python3
"""
Simple SMTP Connectivity Test
Tests basic network connectivity to SMTP server
"""
import socket
import ssl
import sys

def test_smtp_connectivity(host, port):
    """Test basic network connectivity to SMTP server"""
    print(f"Testing connectivity to {host}:{port}...")
    
    try:
        # Test basic TCP connection
        print(f"1. Testing TCP connection...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"   ✅ TCP connection successful")
        else:
            print(f"   ❌ TCP connection failed (error code: {result})")
            return False
        
        # Test SSL/TLS if port is 465 or 587
        if port in [465, 587]:
            print(f"2. Testing SSL/TLS connection...")
            try:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                sock.connect((host, port))
                
                if port == 465:
                    # SSL connection
                    ssl_sock = context.wrap_socket(sock, server_hostname=host)
                    print(f"   ✅ SSL connection successful")
                else:
                    # TLS connection
                    ssl_sock = context.wrap_socket(sock, server_hostname=host)
                    print(f"   ✅ TLS connection successful")
                
                ssl_sock.close()
            except Exception as e:
                print(f"   ⚠️  SSL/TLS connection issue: {str(e)}")
                print(f"   (This might be normal if server requires SMTP protocol handshake first)")
        
        print()
        print("=" * 60)
        print("✅ Basic connectivity test passed!")
        print("=" * 60)
        print("The server is reachable. If email sending still fails,")
        print("the issue is likely with authentication or SMTP protocol.")
        return True
        
    except socket.timeout:
        print(f"   ❌ Connection timeout")
        print()
        print("Possible causes:")
        print("  - Firewall blocking outbound SMTP connections")
        print("  - Network connectivity issues")
        print("  - SMTP server is down or unreachable")
        print("  - Your IP address may be blocked")
        return False
    except Exception as e:
        print(f"   ❌ Connection failed: {str(e)}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test SMTP server connectivity")
    parser.add_argument("--host", required=True, help="SMTP host")
    parser.add_argument("--port", type=int, required=True, help="SMTP port")
    
    args = parser.parse_args()
    
    print()
    print("=" * 60)
    print("SMTP Connectivity Test")
    print("=" * 60)
    print()
    
    success = test_smtp_connectivity(args.host, args.port)
    print()
    sys.exit(0 if success else 1)

