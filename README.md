# 🚀 Conut AI Chief of Operations

**AI-Driven Operations Intelligence System for Conut Café Chain**

An end-to-end AI system addressing 5 critical business objectives through ML-powered analysis of real operational data.

> **Team 503 · AUB AI Engineering Hackathon**  
> Professor Ammar Mohanna

---

## 📋 Quick Start

### 1. Create Virtual Environment
```bash
python -m venv .venv
```

### 2. Activate Virtual Environment
**Windows:**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Mac/Linux:**
```bash
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the System
```bash
python main.py
```

### 5. Access the API
- **Interactive Docs**: http://localhost:8000/docs
- **API Root**: http://localhost:8000
- **Health Check**: http://localhost:8000/health

---

## 📁 Project Structure

```
503-Hackathon/
├── main.py                              # 🌟 Main API server (run this!)
├── requirements.txt                      # Python dependencies
├── .venv/                               # Virtual environment
│
├── data/                                # CSV data files
│   ├── REP_S_00502.csv                  # Sales by customer
│   ├── rep_s_00334_1_SMRY.csv           # Monthly sales
│   ├── REP_S_00461.csv                  # Attendance logs
│   └── ...                              # Other data files
│
├── src/                                 # Source code
│   ├── objective_1_combos.py            # ✅ Combo optimization (ML)
│   ├── objective_2_demand_forecast.py   # ⚠️ Demand forecasting (placeholder)
│   ├── objective_3_expansion.py         # ✅ Expansion analysis
│   ├── objective_4_staffing.py          # ✅ Staffing estimation
│   ├── objective_5_growth_strategy.py   # ✅ Growth strategy
│   └── data_loader.py                   # CSV loading utilities
│
└── docs/                                # Documentation
    ├── RUNNING_SYSTEM_GUIDE.md
    ├── SYSTEM_ANALYSIS_AND_GAPS.md
    └── ...
```

---

## 🎯 Business Objectives

### ✅ Objective 1: Combo Optimization
**Status**: Complete with ML (Apriori Algorithm)
- Identifies optimal product combinations from customer purchasing patterns
- Uses association rule mining (support, confidence, lift)
- **ML Model**: Apriori algorithm (mlxtend)
- **API**: `/api/combos/analysis`

**Key Results**:
- 136 transactions analyzed
- 35 association rules generated
- Top combo: SINGLE ESPRESSO → HOT drink (lift: 17.00)

### ⚠️ Objective 2: Demand Forecasting
**Status**: Placeholder - Needs Implementation
- Should forecast demand per branch for inventory planning
- Requires time series model (Prophet/XGBoost)
- **API**: `/api/demand-forecast` (currently returns placeholder)

**🚨 Critical Gap**: Only placeholder implemented

### ✅ Objective 3: Branch Expansion Feasibility
**Status**: Complete (Statistical Analysis)
- Evaluates viability of opening new branches
- Multi-dimensional scoring of existing branches
- **API**: `/api/expansion`

**Key Results**:
| Branch | Expansion Score | Monthly Growth |
|--------|----------------|---------------|
| Main Street Coffee | 100 / 100 | +176%/month |
| Conut Jnah | 91 / 100 | +68%/month |
| Conut - Tyre | 49 / 100 | +21%/month |
| Conut | 0 / 100 | -41%/month |

**Recommendation**: Replicate Main Street Coffee model

### ✅ Objective 4: Shift Staffing Estimation
**Status**: Complete (Formula-Based)
- Estimates required employees per shift
- Based on demand and attendance data
- **API**: `/api/staffing/{branch}`

**Key Results**:
| Branch | Staff Productivity | Recommended/Shift |
|--------|-------------------|-------------------|
| Conut Jnah | 5.1M units/staff-hour | 2–3 staff |
| Main Street Coffee | 3.2M units/staff-hour | 2–3 staff |
| Conut - Tyre | — | 2 staff |
| Conut | 50K units/staff-hour | 2 staff |

### ✅ Objective 5: Coffee & Milkshake Growth Strategy
**Status**: Complete (Customer Segmentation)
- Data-driven strategies to increase beverage sales
- Customer segmentation and growth opportunities
- **API**: `/api/growth`

**Key Results**:
| Category | Revenue Share | Revenue |
|----------|--------------|---------|
| ☕ Hot-Coffee Based | 50.7% | 691 M |
| 🥤 Shakes (Milkshake) | 22.9% | 311 M |
| 🧋 Frappes | 16.1% | 219 M |
| 🍹 Hot and Cold Drinks | 10.3% | 139 M |

**Top Opportunities**: PISTACHIO MILKSHAKE (893K/unit), MATCHA FRAPPE (626K/unit)

---

## 🔌 API Endpoints

### Core Endpoints
- `GET /` - System overview
- `GET /health` - Health check
- `GET /ask?query=<text>` - **Natural language queries (OpenClaw)**

### Objective 1: Combos
- `GET /api/combos/analysis` - Full combo analysis
- `GET /api/combos/top?limit=5` - Top N combos
- `GET /api/combos/by-branch/{branch}` - Branch-specific combos

### Objective 2: Demand Forecast
- `GET /api/demand-forecast?branch={branch}&months={n}` - ⚠️ Placeholder

### Objective 3: Expansion
- `GET /api/expansion` - Expansion feasibility analysis

### Objective 4: Staffing
- `GET /api/staffing/{branch}` - Staffing recommendations
  - Branches: `Conut`, `Conut - Tyre`, `Conut Jnah`, `Main Street Coffee`

### Objective 5: Growth
- `GET /api/growth` - Coffee & milkshake growth strategy

---

## 🤖 Natural Language Queries (OpenClaw)

The `/ask` endpoint automatically routes natural language questions to the appropriate objective:

```bash
# Expansion
curl "http://localhost:8000/ask?query=Should we open a new branch?"

# Combos
curl "http://localhost:8000/ask?query=What products go well together?"

# Staffing
curl "http://localhost:8000/ask?query=How many staff do we need at Conut Jnah?"

# Growth
curl "http://localhost:8000/ask?query=How can we increase coffee sales?"
```

---

## 🧪 Testing

### Quick System Check
```bash
python check_system_status.py
```

### Test Unified System
```bash
# Start server first
python main.py

# In another terminal (with .venv activated)
python test_unified_system.py
```

### Manual Testing
```bash
# Health check
curl http://localhost:8000/health

# Top 3 combos
curl "http://localhost:8000/api/combos/top?limit=3"

# Expansion decision
curl http://localhost:8000/api/expansion

# Staffing for Main Street Coffee
curl "http://localhost:8000/api/staffing/Main%20Street%20Coffee"

# Growth strategy
curl http://localhost:8000/api/growth
```

---

## 📊 Data Sources

All data files are in the `data/` folder:

| File | Objective | Purpose |
|------|-----------|---------|
| `REP_S_00502.csv` | 1 | Customer transactions for combo analysis |
| `rep_s_00334_1_SMRY.csv` | 2, 3 | Monthly sales by branch |
| `REP_S_00461.csv` | 4 | Time & attendance logs |
| `rep_s_00191_SMRY.csv` | 5 | Product sales by category |
| `rep_s_00150.csv` | 3, 5 | Customer order history |
| `REP_S_00136_SMRY.csv` | 3 | Division/menu summary |
| `rep_s_00435_SMRY.csv` | 3 | Average sales by menu |
| `REP_S_00194_SMRY.csv` | 3 | Tax summary |

---

## 🔧 Development

### Run Individual Objectives

```bash
# Activate virtual environment first
.\.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate    # Mac/Linux

# Objective 1: Combo Optimization
python src/objective_1_combos.py

# Objective 2: Demand Forecast (placeholder)
python src/objective_2_demand_forecast.py

# Objective 3: Expansion Analysis
python -c "from src.objective_3_expansion import run_expansion_analysis, print_report; print_report(run_expansion_analysis())"

# Objective 4: Staffing
python -c "from src.objective_4_staffing import run_staffing_analysis; run_staffing_analysis()"

# Objective 5: Growth Strategy
python src/objective_5_growth_strategy.py
```

### Check System Status
```bash
python check_system_status.py
```

This will show:
- ✅ Implemented objectives
- ⚠️ Placeholder objectives (Objective 2)
- ML status for each objective
- Available API endpoints

---

## 🛠️ Technology Stack

| Component | Technology |
|-----------|-----------|
| **Framework** | FastAPI 0.104+ |
| **Server** | Uvicorn (ASGI) |
| **Data Processing** | Pandas 2.1+, NumPy 1.26+ |
| **ML - Association Rules** | mlxtend 0.23.0 (Apriori) |
| **ML - General** | scikit-learn 1.3+, XGBoost 2.0+ |
| **Visualization** | Matplotlib 3.8+, Seaborn 0.13+, Plotly 5.18+ |
| **API Validation** | Pydantic |
| **HTTP Client** | httpx |

---

## 📚 Documentation

- **[RUNNING_SYSTEM_GUIDE.md](RUNNING_SYSTEM_GUIDE.md)** - Detailed usage guide
- **[SYSTEM_ANALYSIS_AND_GAPS.md](SYSTEM_ANALYSIS_AND_GAPS.md)** - Complete system analysis
- **[NEXT_STEPS_ACTION_PLAN.md](NEXT_STEPS_ACTION_PLAN.md)** - Implementation roadmap
- **[FILE_ORGANIZATION.md](FILE_ORGANIZATION.md)** - File structure details
- **[REORGANIZATION_SUMMARY.md](REORGANIZATION_SUMMARY.md)** - Recent changes

---

## ⚠️ Known Issues & Next Steps

### Critical Gap
- **Objective 2 (Demand Forecasting)** - Only placeholder implemented
  - Needs: Time series ML model (Prophet, XGBoost, LSTM)
  - Impact: Professor evaluates "ML rigor" - currently only 1/5 objectives has ML

### ML Enhancement Opportunities
| Objective | Current | Potential ML Enhancement |
|-----------|---------|-------------------------|
| 1 - Combos | ✅ Apriori ML | Already has ML |
| 2 - Demand | ❌ None | Prophet/XGBoost time series |
| 3 - Expansion | Statistical | XGBoost classification |
| 4 - Staffing | Formula | Linear regression/XGBoost |
| 5 - Growth | Segmentation | K-means clustering |

### Grade Estimates
- **Current**: 70-75/100
  - 4/5 objectives working (minus Objective 2)
  - Only 1/5 has ML model
  - Good system engineering

- **With Objective 2 ML**: 85-90/100
  - All 5 objectives working
  - 2/5 with ML models
  - Complete system

- **With ML in 3+ objectives**: 90-95/100
  - All objectives working
  - Strong ML rigor
  - Advanced analytics

---

## 📈 Evaluation Criteria

The hackathon evaluates on:

1. **Business Impact** (25 points)
   - Practical recommendations
   - Data-driven insights
   - Actionable strategies

2. **Technical Correctness & ML Rigor** (25 points)
   - Model quality
   - Appropriate algorithms
   - Validation methodology

3. **System Engineering (MLOps)** (20 points)
   - Code organization
   - API design
   - Error handling

4. **OpenClaw Integration** (15 points)
   - Natural language interface
   - Intent detection
   - Response quality

5. **Communication Clarity** (15 points)
   - Documentation
   - Visualizations
   - Presentation

---

## 🚀 Quick Commands

```bash
# Setup
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run
python main.py

# Test
python check_system_status.py
curl http://localhost:8000/health

# Natural language query
curl "http://localhost:8000/ask?query=Should we expand?"
```

---

## 👥 Team

**Team 503** - AUB AI Engineering Hackathon

---

## 📞 Support

For detailed information:
- **Interactive API Docs**: http://localhost:8000/docs (when running)
- **System Status**: `python check_system_status.py`
- **Documentation**: See `docs/` folder

---

## 📝 License

This project is for the AUB AI Engineering Hackathon (Professor Ammar Mohanna).

---

**Made with ❤️ for Conut** 🥐☕
