"""
Test OpenClaw Natural Language Integration
"""
import requests

BASE_URL = "http://localhost:8000"

print("\n" + "="*70)
print("TESTING OPENCLAW NATURAL LANGUAGE QUERIES")
print("="*70)

queries = [
    "Should we open a new branch?",
    "How many staff do we need at Conut Jnah?",
    "What products are frequently bought together?",
    "How can we increase coffee sales?"
]

for i, query in enumerate(queries, 1):
    print(f"\n[Query {i}] {query}")
    print("-" * 70)
    
    try:
        response = requests.get(f"{BASE_URL}/ask", params={"query": query})
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Intent Detected: {data.get('intent', 'N/A')}")
            print(f"  Objective: {data.get('objective', 'N/A')}")
            
            # Show key result
            if 'decision' in data:
                print(f"  Decision: {data['decision']}")
            elif 'recommendation' in data:
                print(f"  Recommendation: {data['recommendation']}")
            elif 'top_combos' in data and data['top_combos']:
                print(f"  Top Combo: {' + '.join(data['top_combos'][0]['products'])}")
            elif 'top_opportunities' in data and data['top_opportunities']:
                print(f"  Top Opportunity: {data['top_opportunities'][0].get('name', 'N/A')}")
        else:
            print(f"✗ Failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")

print("\n" + "="*70)
print("OpenClaw Integration Ready!")
print("="*70)
print("\nTo integrate with OpenClaw:")
print("1. Point OpenClaw to: http://localhost:8000/ask")
print("2. Pass user query as 'query' parameter")
print("3. OpenClaw will receive structured JSON responses")
print("="*70 + "\n")
