#!/usr/bin/env python3
"""
Test script for health check endpoints.
Tests all new health check functionality and validates responses.
"""
import asyncio
import json
import time
import sys
from pathlib import Path

# Add the stream_sniper package to Python path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from stream_sniper.api.api import app
from stream_sniper.api.config import get_config

def test_basic_health_endpoint():
    """Test the basic /health endpoint."""
    print("Testing /health endpoint...")
    
    with TestClient(app) as client:
        response = client.get("/health")
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code in [200, 503]:
            data = response.json()
            print("Response JSON:")
            print(json.dumps(data, indent=2))
            
            # Validate required fields
            required_fields = ["status", "timestamp", "version", "uptime_seconds"]
            for field in required_fields:
                if field not in data:
                    print(f"❌ Missing required field: {field}")
                    return False
            
            print("✅ Basic health endpoint test passed")
            return True
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            return False

def test_detailed_health_endpoint():
    """Test the detailed /health/detailed endpoint."""
    print("\nTesting /health/detailed endpoint...")
    
    with TestClient(app) as client:
        response = client.get("/health/detailed")
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code in [200, 503]:
            data = response.json()
            print("Response JSON (first 500 chars):")
            print(json.dumps(data, indent=2)[:500] + "...")
            
            # Validate required sections
            required_sections = ["status", "timestamp", "version", "components", "system"]
            for section in required_sections:
                if section not in data:
                    print(f"❌ Missing required section: {section}")
                    return False
            
            # Validate components
            if "components" in data:
                expected_components = ["database", "cache", "rate_limiter", "external_apis"]
                for component in expected_components:
                    if component not in data["components"]:
                        print(f"❌ Missing component: {component}")
                        return False
            
            # Validate system metrics
            if "system" in data and "resources" in data["system"]:
                expected_resources = ["cpu_percent", "memory", "disk"]
                for resource in expected_resources:
                    if resource not in data["system"]["resources"]:
                        print(f"❌ Missing system resource: {resource}")
                        return False
            
            print("✅ Detailed health endpoint test passed")
            return True
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            return False

def test_prometheus_metrics_endpoint():
    """Test the Prometheus metrics endpoint."""
    print("\nTesting /metrics/prometheus endpoint...")
    
    with TestClient(app) as client:
        response = client.get("/metrics/prometheus")
        
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
        if response.status_code == 200:
            metrics_text = response.text
            print("Prometheus metrics (first 500 chars):")
            print(metrics_text[:500] + "...")
            
            # Validate Prometheus format
            required_patterns = [
                "# HELP",
                "# TYPE",
                "stream_sniper_component_health",
                "stream_sniper_system_cpu_percent",
                "stream_sniper_system_memory_percent"
            ]
            
            for pattern in required_patterns:
                if pattern not in metrics_text:
                    print(f"❌ Missing Prometheus pattern: {pattern}")
                    return False
            
            # Check content type
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("text/plain"):
                print(f"❌ Incorrect content type: {content_type}")
                return False
            
            print("✅ Prometheus metrics endpoint test passed")
            return True
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            return False

def test_health_endpoint_performance():
    """Test health endpoint performance."""
    print("\nTesting health endpoint performance...")
    
    with TestClient(app) as client:
        # Test basic health endpoint performance
        start_time = time.time()
        response = client.get("/health")
        basic_response_time = (time.time() - start_time) * 1000
        
        print(f"Basic health endpoint response time: {basic_response_time:.2f}ms")
        
        # Test detailed health endpoint performance
        start_time = time.time()
        response = client.get("/health/detailed")
        detailed_response_time = (time.time() - start_time) * 1000
        
        print(f"Detailed health endpoint response time: {detailed_response_time:.2f}ms")
        
        # Test Prometheus metrics endpoint performance
        start_time = time.time()
        response = client.get("/metrics/prometheus")
        prometheus_response_time = (time.time() - start_time) * 1000
        
        print(f"Prometheus metrics endpoint response time: {prometheus_response_time:.2f}ms")
        
        # Validate response times are reasonable
        if basic_response_time > 5000:  # 5 seconds
            print(f"❌ Basic health endpoint too slow: {basic_response_time:.2f}ms")
            return False
        
        if detailed_response_time > 10000:  # 10 seconds
            print(f"❌ Detailed health endpoint too slow: {detailed_response_time:.2f}ms")
            return False
        
        if prometheus_response_time > 10000:  # 10 seconds
            print(f"❌ Prometheus metrics endpoint too slow: {prometheus_response_time:.2f}ms")
            return False
        
        print("✅ Health endpoint performance test passed")
        return True

def test_health_headers():
    """Test health-specific headers."""
    print("\nTesting health-specific headers...")
    
    with TestClient(app) as client:
        response = client.get("/health")
        
        headers = dict(response.headers)
        print(f"Health endpoint headers: {headers}")
        
        # Check for health-specific headers
        if "x-health-check" not in headers:
            print("❌ Missing X-Health-Check header")
            return False
        
        if "x-health-response-time" not in headers:
            print("❌ Missing X-Health-Response-Time header")
            return False
        
        try:
            response_time = float(headers["x-health-response-time"])
            if response_time <= 0:
                print(f"❌ Invalid response time: {response_time}")
                return False
        except ValueError:
            print(f"❌ Invalid response time format: {headers['x-health-response-time']}")
            return False
        
        print("✅ Health headers test passed")
        return True

def main():
    """Run all health endpoint tests."""
    print("=== Stream Sniper Health Check Endpoint Tests ===\n")
    
    config = get_config()
    print(f"API Configuration:")
    print(f"  Title: {config.title}")
    print(f"  Version: {config.version}")
    print(f"  Host: {config.host}:{config.port}")
    print(f"  Cache Enabled: {config.cache.enabled}")
    print(f"  Rate Limiting Enabled: {config.rate_limit.enabled}")
    print(f"  Monitoring Enabled: {config.monitoring.enabled}")
    print()
    
    tests = [
        test_basic_health_endpoint,
        test_detailed_health_endpoint,
        test_prometheus_metrics_endpoint,
        test_health_endpoint_performance,
        test_health_headers
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
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