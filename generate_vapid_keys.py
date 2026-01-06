"""
Generate VAPID keys for Web Push Notifications
Run this script to generate VAPID public and private keys
"""
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64

def generate_vapid_keys():
    """Generate VAPID key pair for web push notifications"""
    
    # Generate EC key pair using P-256 curve (required for VAPID)
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    public_key = private_key.public_key()
    
    # Serialize private key to PEM format (what pywebpush expects)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    # Get public key numbers
    public_numbers = public_key.public_numbers()
    
    # Convert to uncompressed format: 04 + x (32 bytes) + y (32 bytes) = 65 bytes
    x_bytes = public_numbers.x.to_bytes(32, 'big')
    y_bytes = public_numbers.y.to_bytes(32, 'big')
    public_key_bytes = b'\x04' + x_bytes + y_bytes
    
    # Base64url encode (URL-safe base64 without padding)
    public_key_b64url = base64.urlsafe_b64encode(public_key_bytes).decode('utf-8').rstrip('=')
    
    # Convert PEM to single-line format for .env file (replace newlines with \n)
    private_pem_single_line = private_pem.replace('\n', '\\n')
    
    return public_key_b64url, private_pem, private_pem_single_line

if __name__ == "__main__":
    print("=" * 70)
    print("VAPID Keys Generator for Web Push Notifications")
    print("=" * 70)
    print("\nGenerating VAPID key pair...")
    
    public_key, private_key_pem, private_key_single_line = generate_vapid_keys()
    
    print("\n[SUCCESS] Keys generated successfully!")
    print("\n" + "=" * 70)
    print("Add these to your .env file:")
    print("=" * 70)
    print(f"\nVAPID_PUBLIC_KEY={public_key}")
    print(f"VAPID_PRIVATE_KEY={private_key_single_line}")
    print(f"VAPID_EMAIL=mailto:noreply@prontivus.com")
    print("\nNote: Private key is stored as single-line with \\n for newlines")
    print("\n" + "=" * 70)
    print("\n[IMPORTANT] Security Notes:")
    print("   - Keep your private key SECRET (never commit to git)")
    print("   - Public key is safe to share")
    print("   - Restart your backend server after adding keys to .env")
    print("=" * 70)
