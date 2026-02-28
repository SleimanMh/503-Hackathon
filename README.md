# Conut AI Chief of Operations — 503 Hackathon

> **Team 503 · CONUT AI Engineering Hackathon**
> An end-to-end AI operations system covering expansion intelligence, staffing optimisation, combo recommendation, demand forecasting, and beverage growth strategy for the Conut café chain.

---

## 📁 Repository Structure

```
503-Hackathon/
├── src/
│   ├── data_loader.py              # All CSV loaders (7 datasets)
│   ├── expansion_engine.py         # Objective 1 — Branch Expansion Intelligence
│   ├── staffing_engine.py          # Objective 2 — Smart Staffing Optimiser
│   ├── combo_engine.py             # Objective 3 — Combo & Upsell Recommender
│   ├── demand_forecast_engine.py   # Objective 4 — Demand Forecast Engine
│   ├── coffee_milkshake_engine.py  # Objective 5 — Coffee & Milkshake Growth Strategy
│   ├── api.py                      # FastAPI server — OpenClaw integration
│   └── __init__.py
├── notebooks/
│   └── expansion_and_staffing.ipynb  # Full analysis notebook (Figs 1–15)
├── requirements.txt
└── README.md
```

---

## �� Quick Start

```bash
# 1. Clone and enter repo
git clone https://github.com/SleimanMh/503-Hackathon.git
cd 503-Hackathon

# 2. Create & activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate    # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run any engine
python -c "from src.expansion_engine import run_expansion_analysis, print_expansion_report; print_expansion_report(run_expansion_analysis())"
python -c "from src.combo_engine import run_combo_analysis, print_combo_report; print_combo_report(run_combo_analysis())"
python -c "from src.demand_forecast_engine import run_demand_forecast, print_forecast_report; print_forecast_report(run_demand_forecast())"
python -c "from src.coffee_milkshake_engine import run_coffee_milkshake_analysis, print_coffee_milkshake_report; print_coffee_milkshake_report(run_coffee_milkshake_analysis())"

# 5. Start the API server (OpenClaw integration)
python -m uvicorn src.api:app --host 0.0.0.0 --port 8000

# 6. Open the full visual notebook
jupyter notebook notebooks/expansion_and_staffing.ipynb
```

---

## 🎯 Business Objectives & Key Results

### Objective 1 — Branch Expansion Intelligence
**Decision: GO (High Confidence)**

| Branch | Expansion Score | Monthly Growth | Revenue Momentum |
|--------|----------------|----------------|-----------------|
| Main Street Coffee | 100 / 100 | +176%/month | 4.12x |
| Conut Jnah | 91 / 100 | +68%/month | 4.10x |
| Conut - Tyre | 49 / 100 | +21%/month | 0.99x |
| Conut | 0 / 100 | -41%/month | 0.07x |

**Recommendation:** Replicate the **Main Street Coffee** model — TABLE-focused, targeting 3,400+ customer catchment, with delivery capability from day 1.

**Methodology:** 7 signals × weighted z-score model (growth 25%, momentum 20%, customer volume 15%, rev/customer 15%, delivery penetration 10%, repeat rate 10%, volatility −5%)

---

### Objective 2 — Smart Staffing Optimiser
**272 total shifts parsed · 9 anomalies detected**

| Branch | Staff Productivity | Recommended per Shift |
|--------|-------------------|----------------------|
| Conut Jnah | 5.1M units/staff-hour | 2 (off-peak), +1 on peak Fri–Sat |
| Main Street Coffee | 3.2M units/staff-hour | 2 (off-peak), +1 on peak |
| Conut - Tyre | — | 2 per shift |
| Conut | 50K units/staff-hour | 2 per shift — monitor decline |

**Anomaly Alert:** 9 long-shift entries (>14 h) detected — punch-out system requires auto-timeout enforcement.

---

### Objective 3 — Combo & Upsell Recommender
**136 transactions analysed · 35 association rules generated**

| Rule (Antecedent → Consequent) | Lift | Action |
|-------------------------------|------|--------|
| SINGLE ESPRESSO → HOT drink | **17.00** | Bundle as "Espresso + Hot Combo" |
| THE SHARING BOX → TRIPLE CHOCOLATE MINI | **15.11** | Create "Sharing Deal" meal |
| CHIMNEY CAKE → ESPRESSO pairing | high | Feature in POS upsell prompt |

**Top insights:**
- Main Street Coffee yields the richest basket data (142 branch-level rules)
- 35 global rules extracted; top combos should be featured as "Meal Deal" items in POS
- Custom Apriori (min_support=0.03, min_confidence=0.15, min_lift=1.3)

---

### Objective 4 — Demand Forecast Engine
**3-month ensemble forecast (Jan–Mar 2026) with 80% & 95% prediction intervals**

| Branch | Trajectory | Jan 2026 Forecast | MoM Growth |
|--------|-----------|------------------|-----------|
| Main Street Coffee | 🚀 Strongly Accelerating | 4.47 B | +176.2%/mo |
| Conut Jnah | 🚀 Strongly Accelerating | 3.31 B | +67.7%/mo |
| Conut - Tyre | 🚀 Strongly Accelerating | 1.69 B | +21.0%/mo |
| Conut (original) | 📉 Declining | — | −40.8%/mo |

**Network totals:**

| Month | Forecast Units |
|-------|---------------|
| Jan 2026 | 9.47 B |
| Feb 2026 | 13.68 B |
| Mar 2026 | 21.79 B |

*Ensemble = 50% Holt double-exponential smoothing + 30% OLS linear regression + 20% CAGR extrapolation*

---

### Objective 5 — Coffee & Milkshake Growth Strategy
**Total beverage revenue: 1.36 B · 5 actionable strategies**

| Category | Revenue Share | Revenue |
|----------|-------------|---------|
| ☕ Hot-Coffee Based | 50.7% | 691 M |
| 🥤 Shakes (Milkshake) | 22.9% | 311 M |
| 🧋 Frappes | 16.1% | 219 M |
| 🍹 Hot and Cold Drinks | 10.3% | 139 M |

**BCG Opportunity Matrix:**

| Quadrant | Top Items |
|----------|----------|
| ⭐ STAR | OREO MILKSHAKE, HOT CHOCOLATE COMBO, CARAMEL FRAPPE |
| 🚀 OPPORTUNITY | PISTACHIO MILKSHAKE (893K/unit), MATCHA FRAPPE (626K/unit) |
| 🐄 CASH COW | Core espresso range |
| 🐕 DOG (prune) | 12 items recommended for menu removal |

**5 Strategies:** Promote OPPORTUNITYs, defend STARs, coffee pricing/seasonal campaign, milkshake bundles, menu pruning

---

## 🔌 API Reference (OpenClaw Integration)

Start the server: `python -m uvicorn src.api:app --host 0.0.0.0 --port 8000`
Interactive docs: `http://localhost:8000/docs`

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Liveness probe |
| GET | `/expansion` | Full expansion analysis JSON |
| GET | `/staffing/{branch}` | Shift recommendations + anomaly count |
| GET | `/combos?branch=&top_n=10` | Association rules (global or per-branch) |
| GET | `/forecast/{branch}` | 3-month ensemble forecast with CI bands |
| GET | `/coffee-strategy` | Full beverage strategy + opportunity matrix |
| GET | `/ask?query=...` | **NLP intent router** — natural language → engine |

### Example `curl` Commands

```bash
# Health check
curl http://localhost:8000/health

# Natural language queries (OpenClaw hook)
curl "http://localhost:8000/ask?query=should+we+open+a+new+branch"
curl "http://localhost:8000/ask?query=staff+at+Conut+Jnah"
curl "http://localhost:8000/ask?query=which+combos+sell+together"
curl "http://localhost:8000/ask?query=forecast+Main+Street+Coffee"
curl "http://localhost:8000/ask?query=milkshake+strategy"

# Direct endpoints
curl "http://localhost:8000/staffing/Main%20Street%20Coffee"
curl "http://localhost:8000/combos?top_n=5"
curl "http://localhost:8000/forecast/Conut%20Jnah"
curl "http://localhost:8000/coffee-strategy"
```

### Supported `/ask` Intents

| Intent | Example Queries |
|--------|----------------|
| `expansion` | "should we open a new branch", "expansion analysis" |
| `staffing` | "staff at Conut Jnah", "staffing recommendations" |
| `combos` | "which combos sell together", "basket analysis" |
| `forecast` | "forecast Main Street Coffee", "demand prediction" |
| `coffee` | "milkshake strategy", "coffee growth", "beverage revenue" |

---

## 📊 Notebook

`notebooks/expansion_and_staffing.ipynb` contains **15 figures** across 5 parts:

| Part | Figures | Content |
|------|---------|---------|
| Part 1 — Expansion | Fig 1–5 | Branch scores radar, revenue trends, feature heatmap, scorecard |
| Part 2 — Staffing | Fig 6–9 | Shift distribution, attendance heatmap, anomaly timeline, productivity |
| Part 3 — Combos | Fig 10–11 | Association rules lift bar, confidence scatter, uplift dual-axis |
| Part 4 — Forecasting | Fig 12–13 | 4-panel CI forecast, stacked area share evolution |
| Part 5 — Coffee/Milkshake | Fig 14–15 | Revenue donut + top SKUs bar, BCG opportunity matrix |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Data processing | pandas 3.0, numpy 2.4 |
| ML / Statistics | scipy 1.17, scikit-learn 1.5, statsmodels 0.14 |
| Forecasting | Custom Holt DES + OLS + CAGR ensemble |
| Market Basket Analysis | Custom Apriori (pure Python, no mlxtend) |
| Visualisation | matplotlib 3.10, seaborn 0.13, plotly 6.5 |
| API | FastAPI 0.134, uvicorn 0.41 |
| Boosting | XGBoost 3.2 |

---

## 🗂️ Data Sources

| File | Description |
|------|-------------|
| `REP_S_00136_SMRY.csv` | Summary sales by branch & item |
| `rep_s_00150.csv` | Attendance / HR records |
| `rep_s_00191_SMRY.csv` | Item-level sales with division |
| `REP_S_00194_SMRY.csv` | Branch-level monthly totals |
| `rep_s_00334_1_SMRY.csv` | Employee productivity data |
| `rep_s_00435_SMRY.csv` | Additional sales summary |
| `REP_S_00461.csv` | Transaction-level data |
| `REP_S_00502.csv` | Delivery order baskets (MBA) |

---

## 📋 Data Notes

- All numeric values are in **scaled arbitrary units** (not real LBP/USD)
- Patterns, ratios, and relative comparisons are valid; absolute thresholds need recalibration with real figures
- Customer and employee names are anonymised in the dataset
