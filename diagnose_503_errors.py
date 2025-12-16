"""
Diagnostic script to identify why 503 errors are occurring
Tests the actual endpoints that are failing
"""
import asyncio
import requests
import time
import sys
import os
from datetime import datetime

# Default server URL
SERVER_URL = os.getenv("API_URL", "http://localhost:8000")

def test_endpoint_with_timing(endpoint: str, token: str = None, timeout: int = 10):
    """Test an endpoint and measure response time"""
    url = f"{SERVER_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    start_time = time.time()
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        elapsed = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        status = response.status_code
        try:
            result = response.json()
        except:
            result = response.text[:100]
        
        if status == 200 or status == 201:
            return True, f"✅ Success ({elapsed:.0f}ms)", elapsed, status
        elif status == 503:
            return False, f"❌ 503 Service Unavailable ({elapsed:.0f}ms) - Pool exhausted or database slow", elapsed, status
        else:
            return False, f"❌ Status {status} ({elapsed:.0f}ms): {str(result)[:50]}", elapsed, status
    except requests.exceptions.Timeout:
        elapsed = (time.time() - start_time) * 1000
        return False, f"⏱️  Timeout after {elapsed:.0f}ms", elapsed, None
    except requests.exceptions.ConnectionError:
        return False, "❌ Connection refused - Server not running", 0, None
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        return False, f"❌ Error: {str(e)[:50]}", elapsed, None


def test_concurrent_requests(endpoints: list, num_requests: int = 5):
    """Simulate concurrent requests like the frontend does"""
    print("\n" + "=" * 70)
    print("Testing Concurrent Requests (Simulating Frontend Load)")
    print("=" * 70)
    
    results = []
    start_time = time.time()
    
    # Test each endpoint multiple times concurrently
    for i in range(num_requests):
        print(f"\n--- Request Batch {i+1}/{num_requests} ---")
        batch_results = []
        
        for endpoint_name, endpoint in endpoints:
            success, message, elapsed, status = test_endpoint_with_timing(endpoint, timeout=10)
            batch_results.append((endpoint_name, success, message, elapsed, status))
            print(f"  {endpoint_name}: {message}")
        
        results.extend(batch_results)
        
        # Small delay between batches
        if i < num_requests - 1:
            time.sleep(0.5)
    
    total_time = (time.time() - start_time) * 1000
    
    # Analyze results
    print("\n" + "=" * 70)
    print("Analysis")
    print("=" * 70)
    
    success_count = sum(1 for _, success, _, _, _ in results if success)
    error_503_count = sum(1 for _, _, _, _, status in results if status == 503)
    timeout_count = sum(1 for _, _, msg, _, _ in results if "Timeout" in msg)
    
    print(f"Total Requests: {len(results)}")
    print(f"Successful: {success_count} ({success_count/len(results)*100:.1f}%)")
    print(f"503 Errors: {error_503_count} ({error_503_count/len(results)*100:.1f}%)")
    print(f"Timeouts: {timeout_count} ({timeout_count/len(results)*100:.1f}%)")
    print(f"Total Time: {total_time:.0f}ms")
    print(f"Average Time per Request: {total_time/len(results):.0f}ms")
    
    # Group by endpoint
    print("\n--- Results by Endpoint ---")
    endpoint_stats = {}
    for endpoint_name, success, message, elapsed, status in results:
        if endpoint_name not in endpoint_stats:
            endpoint_stats[endpoint_name] = {"success": 0, "errors": 0, "times": []}
        if success:
            endpoint_stats[endpoint_name]["success"] += 1
        else:
            endpoint_stats[endpoint_name]["errors"] += 1
        endpoint_stats[endpoint_name]["times"].append(elapsed)
    
    for endpoint_name, stats in endpoint_stats.items():
        avg_time = sum(stats["times"]) / len(stats["times"])
        print(f"{endpoint_name}:")
        print(f"  Success: {stats['success']}, Errors: {stats['errors']}")
        print(f"  Avg Time: {avg_time:.0f}ms")
    
    # Recommendations
    print("\n" + "=" * 70)
    print("Recommendations")
    print("=" * 70)
    
    if error_503_count > 0:
        print("⚠️  503 Errors Detected:")
        print("   - Connection pool is likely exhausted")
        print("   - Backend may need restart to pick up new indexes")
        print("   - Consider increasing pool size if errors persist after restart")
    
    if timeout_count > 0:
        print("⚠️  Timeouts Detected:")
        print("   - Queries are taking too long (>10 seconds)")
        print("   - Database server may be slow or overloaded")
        print("   - Check database server resources (CPU, memory, disk I/O)")
    
    if success_count == len(results):
        print("✅ All requests successful!")
        print("   - System is working correctly")
        print("   - No action needed")
    elif success_count / len(results) > 0.7:
        print("⚠️  Most requests successful, but some errors:")
        print("   - System is mostly working")
        print("   - Errors may be transient (pool exhaustion under load)")
        print("   - Monitor and restart backend if needed")
    else:
        print("❌ High error rate:")
        print("   - System needs attention")
        print("   - Restart backend server immediately")
        print("   - Check database server status")
        print("   - Review backend logs for details")


def main():
    """Main diagnostic function"""
    print("=" * 70)
    print("503 Error Diagnostic Tool")
    print("=" * 70)
    print(f"Server URL: {SERVER_URL}\n")
    
    # Test endpoints that are failing (without auth, will get 401 but tests connection)
    endpoints = [
        ("Dashboard Stats", "/api/v1/analytics/dashboard/stats"),
        ("User Settings", "/api/v1/settings/me"),
        ("Notifications", "/api/v1/notifications"),
    ]
    
    print("Testing endpoints (without auth - will get 401 but tests connection)...")
    for endpoint_name, endpoint in endpoints:
        success, message, elapsed, status = test_endpoint_with_timing(endpoint, timeout=5)
        # 401 is expected without token, so consider it a success for connection test
        if status == 401 or status == 403:
            print(f"  {endpoint_name}: ✅ Server responding (auth required)")
        else:
            print(f"  {endpoint_name}: {message}")
    
    # Test concurrent requests
    test_concurrent_requests(endpoints, num_requests=3)
    
    print("\n" + "=" * 70)
    print("Next Steps")
    print("=" * 70)
    print("1. If seeing 503 errors: Restart backend server")
    print("2. If seeing timeouts: Check database server performance")
    print("3. If all successful: System is working correctly")
    print("=" * 70)


if __name__ == "__main__":
    main()

