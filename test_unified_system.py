"""
Quick test script for the unified Conut AI system
Run this after starting the server to verify all endpoints work
"""

import requests
import json
import sys

# Run with: python main.py (in another terminal)
BASE_URL = "http://localhost:8000"

def test_endpoint(name, url, expected_keys=None):
    """Test a single endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ SUCCESS - Status: {response.status_code}")
            
            # Check for expected keys if provided
            if expected_keys:
                for key in expected_keys:
                    if key in data:
                        print(f"  ✓ Found key: '{key}'")
                    else:
                        print(f"  ✗ Missing key: '{key}'")
            
            # Show sample of response
            print(f"\nSample response:")
            if isinstance(data, dict):
                # Show first few keys
                sample = {k: v for i, (k, v) in enumerate(data.items()) if i < 5}
                print(json.dumps(sample, indent=2)[:500] + "...")
            else:
                print(str(data)[:500] + "...")
            
            return True
        else:
            print(f"✗ FAILED - Status: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"✗ CONNECTION ERROR - Is the server running?")
        print(f"  Start server with: python unified_main.py")
        return False
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("CONUT AI UNIFIED SYSTEM - ENDPOINT TESTS")
    print("="*60)
    
    results = []
    
    # Test 1: Health Check
    results.append(test_endpoint(
        "Health Check",
        f"{BASE_URL}/health",
        expected_keys=["status", "objectives_loaded"]
    ))
    
    # Test 2: Root endpoint
    results.append(test_endpoint(
        "Root / System Overview",
        f"{BASE_URL}/",
        expected_keys=["service", "objectives", "endpoints"]
    ))
    
    # Test 3: Combo Analysis (Objective 1)
    results.append(test_endpoint(
        "Objective 1: Combo Analysis",
        f"{BASE_URL}/api/combos/top?limit=3",
        expected_keys=["combos", "metric"]
    ))
    
    # Test 4: Expansion Analysis (Objective 3)
    results.append(test_endpoint(
        "Objective 3: Expansion Analysis",
        f"{BASE_URL}/api/expansion",
        expected_keys=["decision", "confidence", "best_template_branch"]
    ))
    
    # Test 5: Staffing Analysis (Objective 4)
    results.append(test_endpoint(
        "Objective 4: Staffing Analysis",
        f"{BASE_URL}/api/staffing/Conut%20Jnah",
        expected_keys=["branch", "staffing_by_shift"]
    ))
    
    # Test 6: Growth Strategy (Objective 5)
    results.append(test_endpoint(
        "Objective 5: Growth Strategy",
        f"{BASE_URL}/api/growth",
        expected_keys=["current_state", "opportunities"]
    ))
    
    # Test 7: Natural Language Query - Expansion
    results.append(test_endpoint(
        "Natural Language: Expansion Query",
        f"{BASE_URL}/ask?query=Should%20we%20open%20a%20new%20branch",
        expected_keys=["query", "intent", "decision"]
    ))
    
    # Test 8: Natural Language Query - Combos
    results.append(test_endpoint(
        "Natural Language: Combo Query",
        f"{BASE_URL}/ask?query=What%20products%20are%20bought%20together",
        expected_keys=["query", "intent", "top_combos"]
    ))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nPassed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n✓ ALL TESTS PASSED! System is fully operational.")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Check the output above.")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
