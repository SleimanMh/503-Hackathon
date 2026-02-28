# Conut AI Chief of Operations

AI-Driven Operations Intelligence System for the Conut cafe chain. Turns real sales and attendance data into actionable business decisions across 5 objectives, with a natural language interface via OpenClaw.

> **Team 503 - AUB AI Engineering Hackathon**
> Professor Ammar Mohanna

---

## How to Run

```bash
# 1. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows
# source .venv/bin/activate          # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
python main.py
```

Access the system at:
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Natural Language: http://localhost:8000/ask?query=Should we open a new branch?

---

## Business Objectives

### Objective 1 - Combo Optimization
Identifies which products are frequently purchased together using association rule mining (Apriori algorithm). Helps design bundles and cross-sell promotions.

- **API**: `GET /api/combos/analysis`
- **Result**: 409 combos found. Top pair: DELIVERY CHARGE + NUTELLA SPREAD CHIMNEY

### Objective 2 - Demand Forecasting
Forecasts demand per branch using time-series analysis on monthly sales data. Detects trends, seasonal patterns, and calculates growth rates with confidence intervals to support inventory and supply chain decisions.

- **API**: `GET /api/forecast/demand?branch={branch}&months={n}` — branch forecast with confidence intervals
- **API**: `GET /api/forecast/all-branches` — compare demand across all branches
- **API**: `GET /api/forecast/trends?branch={branch}` — historical trend analysis
- **API**: `GET /api/forecast/accuracy` — model performance metrics
- **Method**: Linear trend fitting + moving averages + seasonality detection
- **Data**: Monthly sales by branch (`rep_s_00334_1_SMRY.csv`)

### Objective 3 - Branch Expansion Feasibility
Scores each branch across multiple dimensions to determine if opening a new branch is viable and which existing branch to replicate.

- **API**: `GET /api/expansion`
- **Result**: GO decision. Replicate Main Street Coffee (score: 100/100, +176% monthly growth)

### Objective 4 - Shift Staffing Estimation
Recommends how many employees are needed per shift at each branch, based on demand patterns and attendance data.

- **API**: `GET /api/staffing/{branch}`
- **Result**: 2-3 staff per shift depending on branch productivity

### Objective 5 - Coffee and Milkshake Growth Strategy
Segments customers and identifies top revenue opportunities to grow beverage sales, with 12-month projections.

- **API**: `GET /api/growth`
- **Result**: Hot-Coffee leads at 50.7% revenue share. Top opportunity: PISTACHIO MILKSHAKE

---

## OpenClaw Integration

[OpenClaw](https://openclaw.ai) is a personal AI assistant that runs locally and connects to Telegram, WhatsApp, or Discord. We provide a **skill** (`skills/conut-ops/SKILL.md`) that lets OpenClaw query our system using natural language.

### How It Works

```
User on Telegram: "Should we open a new branch?"
        |
    OpenClaw (local)
        |  conut-ops skill
    GET http://localhost:8000/ask?query=Should we open a new branch?
        |
    FastAPI detects intent -> routes to Objective 3 (Expansion)
        |
    OpenClaw replies: "GO. Replicate Main Street Coffee."
```

### Natural Language Queries

The `/ask` endpoint accepts any operational question and automatically routes it:

```bash
curl "http://localhost:8000/ask?query=Should we open a new branch?"
curl "http://localhost:8000/ask?query=How many staff do we need at Conut Jnah?"
curl "http://localhost:8000/ask?query=What products go well together?"
curl "http://localhost:8000/ask?query=How can we increase coffee sales?"
```

### Setup OpenClaw Skill

```powershell
# 1. Install OpenClaw
iwr -useb https://openclaw.ai/install.ps1 | iex

# 2. Copy skill
Copy-Item -Recurse ".\skills\conut-ops" "$env:USERPROFILE\.openclaw\skills\conut-ops"

# 3. Start server
python main.py

# 4. In OpenClaw chat, type /reload then ask any question
```

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /ask?query=...` | Natural language query (OpenClaw entry point) |
| `GET /api/combos/analysis` | Full combo analysis |
| `GET /api/combos/top?limit=5` | Top N product combos |
| `GET /api/combos/by-branch/{branch}` | Combos for a specific branch |
| `GET /api/expansion` | Branch expansion feasibility |
| `GET /api/staffing/{branch}` | Staffing recommendations |
| `GET /api/forecast/demand` | Demand forecast for a specific branch |
| `GET /api/forecast/all-branches` | Compare demand across all branches |
| `GET /api/forecast/trends` | Historical trend analysis |
| `GET /api/forecast/accuracy` | Model performance metrics |
| `GET /api/growth` | Coffee and milkshake growth strategy |
| `GET /health` | System health check |

Available branches: `Conut`, `Conut - Tyre`, `Conut Jnah`, `Main Street Coffee`

---

## Data Sources

All CSV files are in the `data/` folder:

| File | Used For |
|------|----------|
| `REP_S_00502.csv` | Customer transactions -> Combo analysis |
| `rep_s_00334_1_SMRY.csv` | Monthly sales by branch -> Expansion, Forecasting |
| `REP_S_00461.csv` | Time and attendance -> Staffing |
| `rep_s_00191_SMRY.csv` | Product sales by category -> Growth strategy |
| `rep_s_00150.csv` | Customer order history -> Expansion, Growth |
| `REP_S_00136_SMRY.csv` | Division/menu summary -> Expansion |
| `rep_s_00435_SMRY.csv` | Average sales by menu -> Expansion |
| `REP_S_00194_SMRY.csv` | Tax summary by branch -> Expansion |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| API Framework | FastAPI + Uvicorn |
| Data Processing | Pandas, NumPy |
| ML - Combos | Apriori association rule mining (mlxtend) |
| ML - General | scikit-learn, XGBoost |
| OpenClaw | Skills-based natural language integration |
| Validation | Pydantic |

---

## Project Structure

```
503-Hackathon/
|-- main.py                             # Main API server (run this)
|-- requirements.txt                    # Dependencies
|-- data/                               # CSV data files
|-- src/
|   |-- objective_1_combos.py           # Combo optimization
|   |-- objective_2_demand_forecast.py  # Demand forecasting
|   |-- objective_3_expansion.py        # Branch expansion
|   |-- objective_4_staffing.py         # Shift staffing
|   |-- objective_5_growth_strategy.py  # Growth strategy
|   `-- data_loader.py                  # CSV parsing utilities
`-- skills/
    `-- conut-ops/
        `-- SKILL.md                    # OpenClaw skill definition
```

Here are the screenshots taken from Open Claw:
<img width="2549" height="1115" alt="Screenshot 2026-02-28 202248" src="https://github.com/user-attachments/assets/1ff7713a-b63c-4849-99ec-9493a43f847b" />
<img width="2559" height="1101" alt="Screenshot 2026-02-28 202237" src="https://github.com/user-attachments/assets/51d39aab-af20-4f21-9492-5574f1dfe412" />
<img width="2559" height="1411" alt="Screenshot 2026-02-28 191012" src="https://github.com/user-attachments/assets/5999bc67-24da-43c5-acc5-159fb89df4b6" />
<img width="2556" height="1506" alt="Screenshot 2026-02-28 202300" src="https://github.com/user-attachments/assets/a84451e2-d199-41e2-a1ac-c237c4f993e1" />
