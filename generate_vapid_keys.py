"""
Generate VAPID keys for web push notifications
Run this script to generate VAPID public and private keys

Usage:
    python generate_vapid_keys.py

Requirements:
    - cryptography (already in requirements.txt)
"""
import base64

def generate_vapid_keys():
    """Generate VAPID keys for web push notifications using cryptography library"""
    try:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
        
        # Generate EC key pair (P-256 curve, same as SECP256R1)
        private_key_obj = ec.generate_private_key(ec.SECP256R1(), default_backend())
        public_key_obj = private_key_obj.public_key()
        
        # Get public key in uncompressed point format (65 bytes: 0x04 + 32 bytes X + 32 bytes Y)
        public_key_bytes = public_key_obj.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        
        # Get private key in PEM format (for pywebpush, we store as PEM string)
        private_key_pem = private_key_obj.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        # Convert to base64 URL-safe format (VAPID standard)
        # Public key: base64url encode the 65-byte uncompressed point
        public_key_b64 = base64.urlsafe_b64encode(public_key_bytes).decode('utf-8').rstrip('=')
        
        # Private key: For VAPID with pywebpush, we can store as PEM string or base64url
        # pywebpush accepts PEM format directly, but for .env we'll base64url encode it
        # The push_service will decode it back to PEM when needed
        private_key_b64 = base64.urlsafe_b64encode(private_key_pem.encode('utf-8')).decode('utf-8').rstrip('=')
        
        print("=" * 60)
        print("VAPID Keys Generated Successfully")
        print("=" * 60)
        print("\nAdd these to your .env file:\n")
        print(f"VAPID_PUBLIC_KEY={public_key_b64}")
        print(f"VAPID_PRIVATE_KEY={private_key_b64}")
        print(f"VAPID_EMAIL=mailto:noreply@prontivus.com")
        print("\n" + "=" * 60)
        print("⚠️  IMPORTANT: Keep these keys secure and never commit them to version control!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Copy the keys above to your .env file")
        print("2. Install pywebpush: pip install pywebpush")
        print("3. Run database migration: alembic upgrade head")
        print("=" * 60)
        
        return {
            "public_key": public_key_b64,
            "private_key": private_key_b64
        }
        
    except ImportError as e:
        print("=" * 60)
        print("Error: cryptography library not installed")
        print("=" * 60)
        print("\nInstall it with:")
        print("  pip install cryptography")
        print(f"\nDetails: {str(e)}")
        return None
    except Exception as e:
        print("=" * 60)
        print("Error generating VAPID keys")
        print("=" * 60)
        print(f"\nDetails: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    generate_vapid_keys()

