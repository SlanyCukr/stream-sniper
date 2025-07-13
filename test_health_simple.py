#!/usr/bin/env python3
"""
Simple test script for health check endpoints without external dependencies.
Tests the endpoints by temporarily disabling rate limiting and caching.
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the stream_sniper package to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment variables to disable external dependencies
os.environ['CACHE_ENABLED'] = 'false'
os.environ['RATE_LIMIT_ENABLED'] = 'false'
os.environ['MONITORING_ENABLED'] = 'false'

from fastapi.testclient import TestClient

def test_health_endpoints_without_dependencies():
    """Test health endpoints with mocked dependencies."""
    print("=== Testing Health Endpoints (Mocked Dependencies) ===\n")
    
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
        
        # Import app after setting up mocks
        from stream_sniper.api.api import app
        
        with TestClient(app) as client:
            # Test basic health endpoint
            print("Testing /health endpoint...")
            response = client.get("/health")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Basic health endpoint responded successfully")
                print(f"Status: {data.get('status')}")
                print(f"Version: {data.get('version')}")
                
                # Check required fields
                required_fields = ["status", "timestamp", "version"]
                missing_fields = [f for f in required_fields if f not in data]
                if missing_fields:
                    print(f"❌ Missing fields: {missing_fields}")
                    return False
            else:
                print(f"❌ Unexpected status code: {response.status_code}")
                return False
            
            # Test detailed health endpoint
            print("\nTesting /health/detailed endpoint...")
            response = client.get("/health/detailed")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Detailed health endpoint responded successfully")
                
                # Check structure
                if "components" in data:
                    components = data["components"]
                    expected_components = ["database", "cache", "rate_limiter"]
                    found_components = [c for c in expected_components if c in components]
                    print(f"Found components: {found_components}")
                    
                if "system" in data:
                    print("✅ System metrics included")
                    
            else:
                print(f"❌ Unexpected status code: {response.status_code}")
                return False
                
            # Test Prometheus metrics endpoint
            print("\nTesting /metrics/prometheus endpoint...")
            response = client.get("/metrics/prometheus")
            print(f"Status Code: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type')}")
            
            if response.status_code == 200:
                metrics_text = response.text
                print("✅ Prometheus metrics endpoint responded successfully")
                
                # Check for basic Prometheus format
                if "# HELP" in metrics_text and "# TYPE" in metrics_text:
                    print("✅ Valid Prometheus format detected")
                else:
                    print("❌ Invalid Prometheus format")
                    return False
                    
                # Show sample metrics
                lines = metrics_text.split('\n')[:10]
                print(f"Sample metrics (first 10 lines):")
                for line in lines:
                    if line.strip():
                        print(f"  {line}")
                        
            else:
                print(f"❌ Unexpected status code: {response.status_code}")
                return False
            
    print("\n✅ All health endpoint tests passed!")
    return True

def test_health_status_enum_values():
    """Test that health status enum values are working correctly."""
    print("\nTesting health status enum values...")
    
    from stream_sniper.api.health import HealthStatus
    
    expected_statuses = ["healthy", "degraded", "unhealthy", "critical", "unknown"]
    actual_statuses = [status.value for status in HealthStatus]
    
    for status in expected_statuses:
        if status not in actual_statuses:
            print(f"❌ Missing health status: {status}")
            return False
    
    print(f"✅ All health status values found: {actual_statuses}")
    return True

def test_health_checker_initialization():
    """Test that health checker can be initialized."""
    print("\nTesting health checker initialization...")
    
    try:
        from stream_sniper.api.health import get_health_checker
        health_checker = get_health_checker()
        
        # Test that it has required methods
        required_methods = [
            'check_database_health',
            'check_cache_health', 
            'get_basic_health',
            'get_detailed_health',
            'generate_prometheus_metrics'
        ]
        
        for method in required_methods:
            if not hasattr(health_checker, method):
                print(f"❌ Missing method: {method}")
                return False
        
        print("✅ Health checker initialized successfully with all required methods")
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize health checker: {e}")
        return False

def main():
    """Run all simplified health tests."""
    tests = [
        test_health_status_enum_values,
        test_health_checker_initialization,
        test_health_endpoints_without_dependencies
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All health check tests passed!")
        return True
    else:
        print("❌ Some health check tests failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)