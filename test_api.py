import urllib.request
import json

def test_endpoint(url, method='GET', data=None):
    try:
        if method == 'GET':
            with urllib.request.urlopen(url) as response:
                content = response.read().decode('utf-8')
                return json.loads(content)
        else:
            req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'),
                                       headers={'Content-Type': 'application/json'},
                                       method=method)
            with urllib.request.urlopen(req) as response:
                content = response.read().decode('utf-8')
                return json.loads(content)
    except Exception as e:
        return {"error": str(e)}

print("\n=== Testing Conut AI OpenClaw API ===\n")

# Test 1: Root endpoint
print("1. Testing root endpoint (/)...")
result = test_endpoint("http://localhost:8000/")
print(json.dumps(result, indent=2))

# Test 2: Health check for Objective 5
print("\n2. Testing Objective 5 health check (/test/objective5)...")
result = test_endpoint("http://localhost:8000/test/objective5")
print(json.dumps(result, indent=2))

# Test 3: Growth recommendations
print("\n3. Testing growth recommendations (/api/growth-recommendations)...")
result = test_endpoint("http://localhost:8000/api/growth-recommendations", "POST", {
    "category": "all",
    "branch": "all"
})
print(json.dumps(result, indent=2))

# Test 4: Agent query
print("\n4. Testing agent query (/agent/query)...")
result = test_endpoint("http://localhost:8000/agent/query?question=What+are+the+coffee+and+milkshake+growth+strategies")
print(json.dumps(result, indent=2))

# Test 5: Dashboard summary
print("\n5. Testing dashboard summary (/dashboard/summary)...")
result = test_endpoint("http://localhost:8000/dashboard/summary")
print(json.dumps(result, indent=2))

print("\n=== All tests completed ===")
