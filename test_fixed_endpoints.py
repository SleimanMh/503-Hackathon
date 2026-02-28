"""
Quick test script to verify all fixed endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8001"

print("="*70)
print("TESTING FIXED API ENDPOINTS")
print("="*70)

# Test 1: Growth endpoint
print("\n1. Testing /api/growth...")
try:
    response = requests.get(f"{BASE_URL}/api/growth")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ SUCCESS - Status: {data.get('status')}")
        print(f"   - Objective: {data.get('objective')}")
        print(f"   - Current coffee %: {data.get('current_state', {}).get('coffee_pct')}%")
        print(f"   - Current milkshake %: {data.get('current_state', {}).get('milkshake_pct')}%")
        print(f"   - Strategies found: {len(data.get('strategies', []))}")
    else:
        print(f"   ✗ FAILED - Status {response.status_code}: {response.json()}")
except Exception as e:
    print(f"   ✗ ERROR: {e}")

# Test 2: Combo analysis endpoint
print("\n2. Testing /api/combos/analysis...")
try:
    response = requests.get(f"{BASE_URL}/api/combos/analysis")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ SUCCESS")
        print(f"   - Total transactions: {data.get('total_transactions')}")
        print(f"   - Unique products: {data.get('unique_products')}")
        print(f"   - Total combos found: {data.get('total_combos_found')}")
        print(f"   - Top combo: {data.get('top_combos', [{}])[0].get('products', 'N/A') if data.get('top_combos') else 'None'}")
    else:
        print(f"   ✗ FAILED - Status {response.status_code}: {response.json()}")
except Exception as e:
    print(f"   ✗ ERROR: {e}")

# Test 3: Branch-specific combos (with fuzzy matching)
print("\n3. Testing /api/combos/by-branch/Jnah (fuzzy match)...")
try:
    response = requests.get(f"{BASE_URL}/api/combos/by-branch/Jnah")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ SUCCESS - Fuzzy matching worked!")
        print(f"   - Query branch: {data.get('query_branch')}")
        print(f"   - Matched branch: {data.get('branch')}")
        print(f"   - Total combos: {data.get('total_combos')}")
        if data.get('combos'):
            print(f"   - Top combo: {data['combos'][0].get('products')}")
    else:
        print(f"   ✗ FAILED - Status {response.status_code}: {response.json()}")
except Exception as e:
    print(f"   ✗ ERROR: {e}")

# Test 4: Other branch variations
test_branches = ["Main Street", "Tyre", "Conut"]
print("\n4. Testing other branch fuzzy matches...")
for branch_query in test_branches:
    try:
        response = requests.get(f"{BASE_URL}/api/combos/by-branch/{branch_query}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ '{branch_query}' → '{data.get('branch')}' ({data.get('total_combos')} combos)")
        else:
            print(f"   ✗ '{branch_query}' failed: {response.status_code}")
    except Exception as e:
        print(f"   ✗ '{branch_query}' error: {e}")

print("\n" + "="*70)
print("TESTING COMPLETE")
print("="*70)
