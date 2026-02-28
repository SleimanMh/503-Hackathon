---
name: conut-ops
description: AI Chief of Operations for Conut café chain. Answers business questions about branch expansion, shift staffing, product combos, demand forecasting, and coffee/milkshake growth strategy using real sales data.
---

# Conut AI Operations Skill

You have access to the Conut AI Operations system — an AI-powered decision engine for the Conut café chain.

## How to Use

To answer any operational question about Conut, call the API endpoint:

```
GET http://localhost:8000/ask?query=<your question>
```

Use `bash` or `curl` to call it. Example:

```bash
curl "http://localhost:8000/ask?query=Should we open a new branch?"
```

## What You Can Ask

This system handles 5 business objectives:

### 1. Branch Expansion
Any question about opening new branches, locations, feasibility.

Example queries:
- "Should we open a new branch?"
- "Which branch should we replicate?"
- "Is expansion feasible?"

### 2. Shift Staffing
Questions about how many employees are needed per shift at each branch.

Example queries:
- "How many staff do we need at Conut Jnah?"
- "What is the recommended headcount for Main Street Coffee evening shift?"
- "How many employees are needed tomorrow?"

Available branches: `Conut`, `Conut - Tyre`, `Conut Jnah`, `Main Street Coffee`

### 3. Product Combos
Questions about which products are frequently bought together, bundling, or cross-selling.

Example queries:
- "What products go well together?"
- "What are the best product combinations?"
- "What should we bundle for promotions?"

### 4. Demand Forecast
Questions about predicting future demand per branch.

Example queries:
- "What is the demand forecast for next month?"
- "Predict sales for Conut Jnah"

### 5. Coffee & Milkshake Growth
Questions about increasing beverage sales, growth strategies, customer segments.

Example queries:
- "How can we increase coffee sales?"
- "What is the growth strategy for milkshakes?"
- "Which beverages have the most potential?"

## Reading the Response

The API returns JSON. Key fields to report to the user:

- `intent` — what objective was detected
- `objective` — objective number (1–5)
- `decision` — for expansion: GO or NO-GO
- `recommendation` — plain-text recommendation
- `top_combos` — for combo queries: list of product pairs
- `top_opportunities` — for growth queries: highest potential items
- `staffing_by_shift` — for staffing: employees per shift

## Example Full Flow

User asks: *"Should Conut open a new branch?"*

You run:
```bash
curl "http://localhost:8000/ask?query=Should%20Conut%20open%20a%20new%20branch"
```

Response will contain:
```json
{
  "intent": "expansion",
  "objective": 3,
  "decision": "GO",
  "best_template_branch": "Main Street Coffee",
  "recommendation": "Decision: GO. Best model: Main Street Coffee"
}
```

You then tell the user: **"Yes, Conut should expand. The recommended model branch to replicate is Main Street Coffee, which scored 100/100 with 176% monthly growth."**

## Health Check

To verify the system is running:
```bash
curl http://localhost:8000/health
```

If the server is not running, tell the user to start it with:
```bash
cd C:\Users\sleim\Downloads\503-Hackathon
.\.venv\Scripts\Activate.ps1
python main.py
```

## All Available Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /ask?query=...` | Natural language query (main entry point) |
| `GET /api/expansion` | Branch expansion analysis |
| `GET /api/staffing/{branch}` | Staffing for a specific branch |
| `GET /api/combos/analysis` | Full combo analysis |
| `GET /api/combos/top?limit=5` | Top N product combos |
| `GET /api/growth` | Coffee & milkshake growth strategy |
| `GET /health` | System health check |
