"""
Test FastAPI server connection and endpoints
"""
import requests
import sys
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Default server URL
SERVER_URL = os.getenv("API_URL", "http://localhost:8000")


def test_endpoint(method: str, endpoint: str, token: str = None, data: dict = None, timeout: int = 10):
    """Test a single endpoint"""
    url = f"{SERVER_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        start_time = datetime.now()
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=timeout)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=timeout)
        else:
            return False, f"Unsupported method: {method}", 0
        
        elapsed = (datetime.now() - start_time).total_seconds()
        status = response.status_code
        
        try:
            result = response.json()
        except:
            result = response.text
        
        if status == 200 or status == 201:
            return True, f"✅ Success ({elapsed:.2f}s)", elapsed
        else:
            return False, f"❌ Status {status}: {str(result)[:100]}", elapsed
    except requests.exceptions.Timeout:
        elapsed = (datetime.now() - start_time).total_seconds()
        return False, f"⏱️  Timeout after {elapsed:.2f}s", elapsed
    except requests.exceptions.ConnectionError:
        return False, "❌ Connection refused - Server not running", 0
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds() if 'start_time' in locals() else 0
        return False, f"❌ Error: {str(e)[:100]}", elapsed


def test_server():
    """Test server connection and endpoints"""
    print("=" * 70)
    print("FastAPI Server Connection Test")
    print("=" * 70)
    print(f"Server URL: {SERVER_URL}\n")
    
    # Test 1: Health check / ping
    print("1. Testing server health check...")
    success, message, elapsed = test_endpoint("GET", "/api/v1/analytics/ping", timeout=5)
    print(f"   {message}")
    if not success:
        print("\n❌ Server is not responding. Make sure the backend server is running.")
        print("   Start the server with: python -m uvicorn main:app --reload")
        return False
    
    # Test 2: Analytics ping (no auth required)
    print("\n2. Testing analytics ping endpoint...")
    success, message, elapsed = test_endpoint("GET", "/api/v1/analytics/ping", timeout=5)
    print(f"   {message}")
    
    # Test 3: Test endpoints that require authentication (will fail but test connection)
    print("\n3. Testing authenticated endpoints (will fail without token, but tests connection)...")
    
    endpoints_to_test = [
        ("GET", "/api/v1/analytics/dashboard/stats", "Dashboard stats"),
        ("GET", "/api/v1/settings/me", "User settings"),
        ("GET", "/api/v1/notifications", "Notifications"),
    ]
    
    results = []
    for method, endpoint, name in endpoints_to_test:
        success, message, elapsed = test_endpoint(method, endpoint, timeout=30)
        # For auth endpoints, 401 is expected without token, so we check if server responded
        if "401" in message or "403" in message or success:
            status = "✅ Server responding"
        elif "Timeout" in message:
            status = f"⏱️  Timeout ({elapsed:.2f}s)"
        else:
            status = f"⚠️  {message}"
        results.append((name, status, elapsed))
        print(f"   {name}: {status}")
        
        # Test 4: Concurrent requests (simulating login scenario)
        print("\n4. Testing concurrent requests (simulating login)...")
        
        def test_concurrent_endpoint(endpoint_name: str, endpoint: str):
            success, message, elapsed = test_endpoint("GET", endpoint, timeout=30)
            return endpoint_name, success, message, elapsed
        
        endpoints = [
            ("Dashboard", "/api/v1/analytics/dashboard/stats"),
            ("Settings", "/api/v1/settings/me"),
            ("Notifications", "/api/v1/notifications"),
        ]
        
        concurrent_results = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(test_concurrent_endpoint, name, endpoint) 
                      for name, endpoint in endpoints]
            for future in as_completed(futures):
                try:
                    result = future.result()
                    concurrent_results.append(result)
                except Exception as e:
                    concurrent_results.append((f"Error", False, f"Exception: {e}", 0))
        
        success_count = 0
        for name, success, message, elapsed in concurrent_results:
            # 401/403 means server is responding, just needs auth
            if "401" in message or "403" in message or success:
                status = "✅ Responding"
                success_count += 1
            else:
                status = message
            print(f"   {name}: {status} ({elapsed:.2f}s)")
        
        print("\n" + "=" * 70)
        if success_count == len(concurrent_results):
            print("✅ Server connection test passed!")
            print("   All endpoints are responding (auth required for full functionality)")
        else:
            print("⚠️  Server is responding but some endpoints may have issues")
        print("=" * 70)
        
        return True


def main():
    """Main function"""
    try:
        test_server()
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to server at {SERVER_URL}")
        print("   Make sure the backend server is running:")
        print("   cd backend")
        print("   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error testing server: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

