# Conut AI Chief of Operations Agent

**Hackathon:** Conut AI Engineering — 12-Hour Challenge
**Focus Areas (this repo):** Expansion Feasibility · Shift Staffing Estimation

---

## Business Problem

Conut is a growing sweets and beverages chain with 4 branches. Leadership needs a data-driven system to:
1. Decide whether to open a 5th branch — and which model to replicate
2. Optimise shift staffing across branches to match demand without over/under-staffing

---

## Architecture

```
503-Hackathon/
├── src/
│   ├── data_loader.py          # Robust CSV ingestion (handles report-style headers, quoted numbers)
│   ├── expansion_engine.py     # Multi-factor branch scoring + expansion recommendation
│   └── staffing_engine.py      # Attendance analytics + demand-driven staffing model
├── notebooks/
│   └── expansion_and_staffing.ipynb   # Full visual analysis with 9 charts
├── *.csv                        # Raw Conut scaled data files
└── README.md
```

---

## Key Results

### Expansion Decision: GO (High Confidence)

| Branch | Expansion Score | Monthly Growth | Revenue Momentum |
|--------|----------------|----------------|-----------------|
| Main Street Coffee | 100 / 100 | +176%/month | 4.12x |
| Conut Jnah | 91 / 100 | +68%/month | 4.10x |
| Conut - Tyre | 49 / 100 | +21%/month | 0.99x |
| Conut | 0 / 100 | -41%/month | 0.07x |

**Recommendation:** Replicate the **Main Street Coffee** model — TABLE-focused, targeting 3,400+ customer catchment, with delivery capability from day 1.

### Staffing Recommendations (Dec 2025 baseline)

| Branch | Staff Productivity | Recommended per Shift |
|--------|-------------------|----------------------|
| Conut Jnah | 5.1M units/staff-hour | 2 (off-peak), +1 on peak Fri-Sat |
| Main Street Coffee | 3.2M units/staff-hour | 2 (off-peak), +1 on peak |
| Conut - Tyre | — | 2 per shift |
| Conut | 50K units/staff-hour | 2 per shift — monitor decline |

**Anomaly Alert:** 9 long-shift entries (>14h) detected across branches — punch-out system requires auto-timeout enforcement.

---

## How to Run

```bash
# 1. Clone and enter repo
git clone https://github.com/SleimanMh/503-Hackathon.git
cd 503-Hackathon

# 2. Install dependencies
pip install pandas numpy scikit-learn matplotlib seaborn scipy statsmodels xgboost plotly

# 3. Run expansion analysis
python src/expansion_engine.py

# 4. Run staffing analysis
python src/staffing_engine.py

# 5. Open the full visual notebook
jupyter notebook notebooks/expansion_and_staffing.ipynb
```

---

## Methodology

### Expansion Feasibility Engine
- **7 signals extracted** per branch from 4 data files
- **Weighted z-score scoring** model (weights tuned to business relevance)
- Signals: monthly growth rate (25%), revenue momentum (20%), customer volume (15%), revenue/customer (15%), delivery penetration (10%), repeat customer rate (10%), volatility penalty (-5%)
- Decision rule: GO if network avg growth >5%/month AND momentum >1.1x

### Shift Staffing Engine
- **Attendance parsing** from Dec 2025 punch-in/out records
- **Shift classification**: Morning / Afternoon / Evening / Graveyard
- **Demand model**: Customer volume x service time per channel / effective hours per shift
- **Peak buffer**: 1.25x on high-demand periods; 0.85x off-peak
- **Anomaly detection**: Long shifts (>14h) flagged for HR review
- **Productivity Index**: Revenue generated per staff-hour cross-referenced against Dec monthly revenue

---

## Data Notes
- All numeric values are in **scaled arbitrary units** (not real LBP/USD)
- Patterns, ratios, and relative comparisons are valid; absolute thresholds need recalibration with real figures
- Customer and employee names anonymised in the dataset
