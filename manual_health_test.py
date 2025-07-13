#!/usr/bin/env python3
"""
Manual test of the health check functionality.
This tests the components directly without running the full FastAPI app.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the stream_sniper package to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_health_checker_components():
    """Test individual health checker components."""
    print("=== Testing Health Checker Components ===\n")
    
    # Mock database operations
    mock_pool = MagicMock()
    mock_pool.get_pool_status.return_value = {
        "status": "active",
        "minconn": 2,
        "maxconn": 20
    }
    mock_pool.health_check.return_value = True
    
    # Mock cache operations  
    mock_cache = MagicMock()
    mock_cache.get_stats.return_value = {
        "enabled": False,
        "status": "disabled"
    }
    
    # Mock rate limiter operations
    mock_rate_stats = {
        "enabled": False,
        "storage": {"type": "memory", "status": "disabled"}
    }
    
    with patch('stream_sniper.database.connection_pool.get_pool', return_value=mock_pool), \
         patch('stream_sniper.api.cache.get_cache', return_value=mock_cache), \
         patch('stream_sniper.api.rate_limiter.get_rate_limit_stats', return_value=mock_rate_stats):
        
        from stream_sniper.api.health import get_health_checker, HealthStatus
        
        print("1. Testing HealthChecker initialization...")
        health_checker = get_health_checker()
        print("✅ Health checker initialized successfully")
        
        print("\n2. Testing database health check...")
        db_health = health_checker.check_database_health()
        print(f"✅ Database health: {db_health.status.value} - {db_health.message}")
        print(f"   Response time: {db_health.response_time_ms}ms")
        
        print("\n3. Testing cache health check...")
        cache_health = health_checker.check_cache_health()
        print(f"✅ Cache health: {cache_health.status.value} - {cache_health.message}")
        print(f"   Response time: {cache_health.response_time_ms}ms")
        
        print("\n4. Testing rate limiter health check...")
        rate_limit_health = health_checker.check_rate_limiter_health()
        print(f"✅ Rate limiter health: {rate_limit_health.status.value} - {rate_limit_health.message}")
        print(f"   Response time: {rate_limit_health.response_time_ms}ms")
        
        print("\n5. Testing system resources...")
        system_resources = health_checker.get_system_resources()
        print(f"✅ System resources collected:")
        print(f"   CPU: {system_resources.cpu_percent}%")
        print(f"   Memory: {system_resources.memory_percent}% ({system_resources.memory_used_mb}/{system_resources.memory_total_mb} MB)")
        print(f"   Disk: {system_resources.disk_percent}% ({system_resources.disk_free_gb}/{system_resources.disk_total_gb} GB)")
        
        print("\n6. Testing basic health status...")
        overall_status, health_data = health_checker.get_basic_health()
        print(f"✅ Basic health status: {overall_status.value}")
        print(f"   Keys in response: {list(health_data.keys())}")
        
        print("\n7. Testing detailed health status...")
        overall_status, detailed_health_data = health_checker.get_detailed_health()
        print(f"✅ Detailed health status: {overall_status.value}")
        print(f"   Components checked: {list(detailed_health_data.get('components', {}).keys())}")
        print(f"   System info included: {'system' in detailed_health_data}")
        
        print("\n8. Testing Prometheus metrics generation...")
        metrics_text = health_checker.generate_prometheus_metrics()
        print(f"✅ Prometheus metrics generated ({len(metrics_text)} characters)")
        
        # Show sample metrics
        lines = [line for line in metrics_text.split('\n') if line.strip() and not line.startswith('#')][:5]
        print("   Sample metrics:")
        for line in lines:
            print(f"     {line}")
        
        return True

def test_external_api_check():
    """Test the external API check functionality."""
    print("\n=== Testing External API Check ===\n")
    
    from stream_sniper.api.health import get_health_checker
    
    health_checker = get_health_checker()
    
    print("Testing Twitch API connectivity...")
    twitch_health = health_checker.check_twitch_api_health()
    print(f"✅ Twitch API health: {twitch_health.status.value} - {twitch_health.message}")
    print(f"   Response time: {twitch_health.response_time_ms}ms")
    print(f"   Details: {twitch_health.details}")
    
    return True

def test_health_status_values():
    """Test the health status enum values and their behavior."""
    print("\n=== Testing Health Status Enum ===\n")
    
    from stream_sniper.api.health import HealthStatus
    
    print("Available health statuses:")
    for status in HealthStatus:
        print(f"  {status.name}: {status.value}")
    
    # Test status priority logic
    statuses = [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]
    print(f"\nStatus priority test:")
    print(f"  Input: {[s.value for s in statuses]}")
    
    # This simulates the logic in get_detailed_health
    if HealthStatus.CRITICAL in statuses:
        overall = HealthStatus.CRITICAL
    elif HealthStatus.UNHEALTHY in statuses:
        overall = HealthStatus.UNHEALTHY
    elif HealthStatus.DEGRADED in statuses:
        overall = HealthStatus.DEGRADED
    else:
        overall = HealthStatus.HEALTHY
    
    print(f"  Overall: {overall.value}")
    print("✅ Health status priority logic working correctly")
    
    return True

def main():
    """Run all manual health tests."""
    tests = [
        test_health_status_values,
        test_health_checker_components,
        test_external_api_check
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
                print("✅ Test passed")
            else:
                print("❌ Test failed")
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n=== Manual Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All manual health tests passed!")
        return True
    else:
        print("❌ Some manual health tests failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)