"""
Diagnostic script to test API endpoint response times
"""
import asyncio
import time
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000")
TEST_TOKEN = os.getenv("TEST_TOKEN", "")  # You'll need to get a valid token

async def test_endpoint(session, endpoint, token=None):
    """Test an endpoint and measure response time"""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    start_time = time.time()
    try:
        async with session.get(
            f"{API_URL}{endpoint}",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            elapsed = time.time() - start_time
            status = response.status
            text = await response.text()
            return {
                "endpoint": endpoint,
                "status": status,
                "time": elapsed,
                "success": status == 200,
                "response_length": len(text)
            }
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        return {
            "endpoint": endpoint,
            "status": "TIMEOUT",
            "time": elapsed,
            "success": False,
            "error": "Request timed out"
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "endpoint": endpoint,
            "status": "ERROR",
            "time": elapsed,
            "success": False,
            "error": str(e)
        }

async def main():
    """Run diagnostic tests"""
    print("=" * 60)
    print("API Timeout Diagnostic Test")
    print("=" * 60)
    print(f"API URL: {API_URL}")
    print()
    
    async with aiohttp.ClientSession() as session:
        # Test public endpoints first
        print("Testing public endpoints...")
        public_endpoints = [
            "/docs",
            "/api/v1/analytics/ping",
        ]
        
        for endpoint in public_endpoints:
            result = await test_endpoint(session, endpoint)
            status_icon = "✓" if result["success"] else "✗"
            print(f"{status_icon} {endpoint:40} {result['time']:.2f}s [{result['status']}]")
        
        print()
        
        # Test authenticated endpoints if token provided
        if TEST_TOKEN:
            print("Testing authenticated endpoints...")
            auth_endpoints = [
                "/api/v1/analytics/dashboard/stats",
                "/api/v1/notifications",
                "/api/v1/settings/me",
            ]
            
            for endpoint in auth_endpoints:
                result = await test_endpoint(session, endpoint, TEST_TOKEN)
                status_icon = "✓" if result["success"] else "✗"
                print(f"{status_icon} {endpoint:40} {result['time']:.2f}s [{result['status']}]")
                if not result["success"] and "error" in result:
                    print(f"    Error: {result['error']}")
        else:
            print("Skipping authenticated endpoints (no TEST_TOKEN provided)")
            print("Set TEST_TOKEN environment variable to test authenticated endpoints")
    
    print()
    print("=" * 60)
    print("Diagnostic complete")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())

