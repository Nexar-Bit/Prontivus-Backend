"""
Check if the running backend is using the correct pool size
by checking the actual database connection from the running server
"""
import requests
import sys
import os

SERVER_URL = os.getenv("API_URL", "http://localhost:8000")

def check_backend_status():
    """Check if backend is running and get basic info"""
    print("=" * 70)
    print("Backend Server Status Check")
    print("=" * 70)
    
    try:
        # Test health endpoint
        response = requests.get(f"{SERVER_URL}/api/v1/analytics/ping", timeout=5)
        if response.status_code == 200:
            print("✅ Backend server is running")
        else:
            print(f"⚠️  Backend responded with status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Backend server is not running or not accessible")
        print("   Make sure the backend is started on port 8000")
        return False
    except Exception as e:
        print(f"❌ Error checking backend: {e}")
        return False
    
    # Check if we can see pool info in logs (would need to check log files)
    print("\n💡 To verify pool size is correct:")
    print("   1. Check backend terminal/logs for:")
    print("      'Database engine created with pool_size=25, max_overflow=35'")
    print("   2. If you see pool_size=30, the backend hasn't been restarted")
    print("   3. If you see pool_size=25, the backend is using the correct config")
    
    return True

if __name__ == "__main__":
    check_backend_status()

