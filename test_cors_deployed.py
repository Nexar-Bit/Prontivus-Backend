"""
Test CORS configuration on deployed backend
"""
import requests
import sys

def test_cors(backend_url: str, frontend_origin: str):
    """Test CORS preflight and actual request"""
    print(f"[TEST] Testing CORS for backend: {backend_url}")
    print(f"   Frontend origin: {frontend_origin}")
    print()
    
    # Test 1: OPTIONS preflight request
    print("[1] Testing OPTIONS preflight request...")
    try:
        response = requests.options(
            f"{backend_url}/api/auth/login",
            headers={
                "Origin": frontend_origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        print(f"   Headers:")
        for key, value in response.headers.items():
            if "access-control" in key.lower() or "cors" in key.lower():
                print(f"      {key}: {value}")
        
        if "Access-Control-Allow-Origin" in response.headers:
            allowed_origin = response.headers["Access-Control-Allow-Origin"]
            if allowed_origin == frontend_origin or allowed_origin == "*":
                print("   [OK] CORS preflight: ALLOWED")
            else:
                print(f"   [ERROR] CORS preflight: BLOCKED (allowed: {allowed_origin})")
        else:
            print("   [ERROR] CORS preflight: NO HEADER FOUND")
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
    
    print()
    
    # Test 2: GET request to health endpoint (no auth needed)
    print("[2] Testing GET request with Origin header...")
    try:
        response = requests.get(
            f"{backend_url}/health",
            headers={
                "Origin": frontend_origin,
            },
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        if "Access-Control-Allow-Origin" in response.headers:
            allowed_origin = response.headers["Access-Control-Allow-Origin"]
            print(f"   Access-Control-Allow-Origin: {allowed_origin}")
            if allowed_origin == frontend_origin or allowed_origin == "*":
                print("   [OK] CORS GET request: ALLOWED")
            else:
                print(f"   [ERROR] CORS GET request: BLOCKED (allowed: {allowed_origin})")
        else:
            print("   [ERROR] CORS GET request: NO HEADER FOUND")
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
    
    print()
    print("=" * 60)
    print()
    print("[SUMMARY]")
    print()
    print("If CORS is blocked, you need to:")
    print("1. Go to Render.com dashboard")
    print("2. Select your backend service")
    print("3. Go to Environment -> Environment Variables")
    print("4. Add/Edit: BACKEND_CORS_ORIGINS")
    print("5. Set value to:")
    print(f'   https://prontivus-frontend-p2rr.vercel.app,https://prontivus-f-pplm.vercel.app,http://localhost:3000')
    print("6. Save and wait for redeploy (~5 minutes)")
    print()

if __name__ == "__main__":
    backend_url = "https://prontivus-backend-8ef1.onrender.com"
    frontend_origin = "https://prontivus-frontend-p2rr.vercel.app"
    
    if len(sys.argv) > 1:
        backend_url = sys.argv[1]
    if len(sys.argv) > 2:
        frontend_origin = sys.argv[2]
    
    test_cors(backend_url, frontend_origin)
