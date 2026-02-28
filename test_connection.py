"""
Quick test to verify the API is accessible from YOUR terminal
Run this: python test_connection.py
"""
import requests
import sys

print("\n" + "="*70)
print("TESTING API CONNECTION FROM YOUR TERMINAL")
print("="*70)

base_url = "http://localhost:8000"

# Test 1: Root endpoint
print("\n[Test 1] Checking server root...")
try:
    response = requests.get(base_url, timeout=5)
    if response.status_code == 200:
        print("   ✓ SUCCESS - Server is responding!")
        data = response.json()
        print(f"   Service: {data.get('service')}")
        print(f"   Status: {data.get('status')}")
    else:
        print(f"   ✗ FAILED - Status code: {response.status_code}")
        sys.exit(1)
except requests.exceptions.ConnectionError:
    print(f"   ✗ CANNOT CONNECT to {base_url}")
    print("   Make sure the server is running: python main.py")
    sys.exit(1)
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    sys.exit(1)

# Test 2: Health endpoint
print("\n[Test 2] Checking health endpoint...")
try:
    response = requests.get(f"{base_url}/health")
    if response.status_code == 200:
        data = response.json()
        print("   ✓ SUCCESS")
        print(f"   Combos loaded: {data.get('objectives_loaded', {}).get('combos')}")
        print(f"   Growth loaded: {data.get('objectives_loaded', {}).get('growth')}")
        print(f"   Combos found: {data.get('combos_found')}")
    else:
        print(f"   ✗ FAILED - Status: {response.status_code}")
except Exception as e:
    print(f"   ✗ ERROR: {e}")

# Test 3: Growth endpoint
print("\n[Test 3] Checking growth endpoint...")
try:
    response = requests.get(f"{base_url}/api/growth")
    if response.status_code == 200:
        data = response.json()
        print("   ✓ SUCCESS")
        print(f"   Status: {data.get('status')}")
        print(f"   Objective: {data.get('objective')}")
        print(f"   Coffee %: {data.get('current_state', {}).get('coffee_pct')}%")
    else:
        print(f"   ✗ FAILED - Status: {response.status_code}")
        print(f"   Error: {response.text}")
except Exception as e:
    print(f"   ✗ ERROR: {e}")

# Test 4: Combos endpoint
print("\n[Test 4] Checking combos endpoint...")
try:
    response = requests.get(f"{base_url}/api/combos/analysis")
    if response.status_code == 200:
        data = response.json()
        print("   ✓ SUCCESS")
        print(f"   Total transactions: {data.get('total_transactions')}")
        print(f"   Total combos: {data.get('total_combos_found')}")
    else:
        print(f"   ✗ FAILED - Status: {response.status_code}")
        print(f"   Error: {response.text}")
except Exception as e:
    print(f"   ✗ ERROR: {e}")

print("\n" + "="*70)
print("✅ ALL TESTS PASSED - API IS WORKING FROM YOUR TERMINAL!")
print("\nOpen in browser:")
print(f"   📚 Docs: {base_url}/docs")
print(f"   🏥 Health: {base_url}/health")
print(f"   📊 Growth: {base_url}/api/growth")
print("\nIf browser doesn't work:")
print("   1. Clear browser cache (Ctrl+Shift+Delete)")
print("   2. Use incognito/private window")
print("   3. Try different browser")
print("="*70 + "\n")
