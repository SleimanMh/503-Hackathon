"""
Conut AI Chief of Operations - Unified API
===========================================
Complete integration of all objectives:
  - Objective 1: Combo Optimization (Product Combinations)
  - Objective 3: Branch Expansion Feasibility
  - Objective 4: Shift Staffing Estimation
  - Objective 5: Coffee & Milkshake Growth Strategy

OpenClaw Integration Ready - Natural Language Query Support
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
import re
from collections import defaultdict, Counter
from itertools import combinations
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ML libraries for combo analysis
try:
    from mlxtend.frequent_patterns import apriori, association_rules
    from mlxtend.preprocessing import TransactionEncoder
    HAS_MLXTEND = True
except ImportError:
    HAS_MLXTEND = False
    print("Warning: mlxtend not installed. Combo analysis will use basic methods.")

# Import objective engines
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.objective_3_expansion import run_expansion_analysis
from src.objective_4_staffing import run_staffing_analysis
from src.objective_2_demand_forecast import run_demand_forecast_analysis

# Import Objective 5 functions
try:
    from src.objective_5_growth_strategy import (
        load_products_by_division,
        load_customers,
        CoffeeAndMilkshakeAnalysis,
        growth_recommendations_endpoint
    )
    HAS_OBJECTIVE_5 = True
except ImportError as e:
    print(f"Warning: Objective 5 module not fully available: {e}")
    HAS_OBJECTIVE_5 = False

# ═══════════════════════════════════════════════════════════════════════════
# FASTAPI APP SETUP
# ═══════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Conut AI Chief of Operations",
    description=(
        "Unified AI-driven operations intelligence for Conut's café chain. "
        "Integrates: Combo Optimization, Branch Expansion, Staffing Analysis, "
        "and Coffee/Milkshake Growth Strategy. OpenClaw integration ready."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS (OBJECTIVE 1 - COMBOS)
# ═══════════════════════════════════════════════════════════════════════════

class ComboRecommendation(BaseModel):
    combo_id: int
    products: List[str]
    frequency: int
    support: float
    avg_revenue: float
    confidence: float
    lift: Optional[float] = None
    ml_generated: bool = False
    branch: Optional[str] = None
    description: str


class ComboAnalysisResponse(BaseModel):
    total_transactions: int
    unique_products: int
    total_combos_found: int
    top_combos: List[ComboRecommendation]
    by_branch: Dict[str, List[ComboRecommendation]]


# ═══════════════════════════════════════════════════════════════════════════
# OBJECTIVE 1: COMBO OPTIMIZATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class ConutDataProcessor:
    """Handles loading and processing Conut sales data"""
    
    def __init__(self, data_dir: str = "."):
        self.data_dir = Path(data_dir)
        self.transactions = []
        self.products = set()
        
    def load_sales_data(self, filename: str = "REP_S_00502.csv") -> pd.DataFrame:
        """Load and clean sales data from CSV"""
        filepath = self.data_dir / filename
        if not filepath.exists():
            # Try alternate location
            filepath = self.data_dir / "data" / filename
            if not filepath.exists():
                raise FileNotFoundError(f"File not found: {filename}")
        
        # Read and parse the file
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        records = []
        current_branch = None
        current_customer = None
        
        for line_raw in lines:
            line_raw = line_raw.rstrip('\n')
            
            # Extract branch (format: "Branch :Conut - Tyre" or "Branch: Name")
            # Must start with "Branch" and not be mostly numeric
            if line_raw.startswith('Branch'):
                branch_match = re.search(r'Branch\s*:\s*(.+?)(?:,|$)', line_raw)
                if branch_match:
                    potential_branch = branch_match.group(1).strip()
                    # Validate: must contain letters, not just numbers/quotes
                    if potential_branch and re.search(r'[a-zA-Z]{3,}', potential_branch):
                        current_branch = potential_branch
                        print(f"  Found branch: {current_branch}")
                continue
            
            # Extract customer (format: "Person_XXXX,,,,")
            if line_raw.startswith('Person_') and ',' in line_raw:
                parts = line_raw.split(',')
                current_customer = parts[0].strip()
                continue
            
            # Skip header and summary lines
            if 'Full Name' in line_raw or 'Total :' in line_raw or 'Page' in line_raw:
                continue
                
            # Parse product lines (format: ",Qty,  Description,Price,")
            if line_raw.startswith(',') and current_branch and current_customer:
                parts = [p.strip() for p in line_raw.split(',')]
                if len(parts) >= 4:
                    try:
                        qty_str = parts[1].strip()
                        product = parts[2].strip()
                        price_str = parts[3].strip()
                        
                        # Skip if not valid data
                        if not product or not qty_str or product.startswith('From Date'):
                            continue
                        
                        # Parse qty and price
                        try:
                            qty = float(qty_str)
                        except ValueError:
                            continue
                            
                        # Only process positive quantities and real products
                        if qty > 0 and product and not product.startswith('['):
                            try:
                                price = float(price_str.replace(',', '').replace('"', ''))
                            except ValueError:
                                price = 0.0
                            
                            records.append({
                                'branch': current_branch,
                                'customer': current_customer,
                                'product': product,
                                'quantity': qty,
                                'price': price
                            })
                            self.products.add(product)
                    except (ValueError, IndexError) as e:
                        continue
        
        df = pd.DataFrame(records)
        print(f"  Loaded {len(df)} product transactions")
        return df


class ComboOptimizer:
    """Analyzes product combinations using ML"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.total_transactions = len(df.groupby(['customer', 'branch']))
        self.total_items = len(df)
        
    def find_combos_ml(self, min_support: float = 0.01, min_confidence: float = 0.1) -> List[Dict]:
        """ML-based combo discovery using Apriori algorithm"""
        if not HAS_MLXTEND:
            return self.find_combos(min_support=min_support)
        
        # Prepare transactions
        transactions = []
        for (customer, branch), group in self.df.groupby(['customer', 'branch']):
            products = group['product'].tolist()
            transactions.append(products)
        
        if not transactions:
            return []
        
        # Apply Apriori
        try:
            te = TransactionEncoder()
            te_ary = te.fit(transactions).transform(transactions)
            df_encoded = pd.DataFrame(te_ary, columns=te.columns_)
            
            frequent_itemsets = apriori(df_encoded, min_support=min_support, use_colnames=True)
            if len(frequent_itemsets) == 0:
                return []
            
            rules = association_rules(frequent_itemsets, metric="confidence", 
                                     min_threshold=min_confidence, num_itemsets=len(frequent_itemsets))
            
            # Convert to combo format
            combos = []
            for idx, rule in rules.iterrows():
                products = list(rule['antecedents']) + list(rule['consequents'])
                frequency = int(rule['support'] * self.total_transactions)
                combo_revenue = self._get_combo_revenue(products)
                
                combos.append({
                    'products': sorted(products),
                    'frequency': frequency,
                    'support': float(rule['support']),
                    'confidence': float(rule['confidence']),
                    'lift': float(rule['lift']),
                    'avg_revenue': combo_revenue,
                    'ml_generated': True
                })
            
            # Remove duplicates
            seen = set()
            unique_combos = []
            for combo in combos:
                key = frozenset(combo['products'])
                if key not in seen:
                    seen.add(key)
                    unique_combos.append(combo)
            
            unique_combos.sort(key=lambda x: (-x['lift'], -x['confidence']))
            return unique_combos
            
        except Exception as e:
            print(f"ML algorithm failed: {e}. Using basic method.")
            return self.find_combos(min_support=min_support)
    
    def find_combos(self, min_support: float = 0.02) -> List[Dict]:
        """Basic combo discovery without ML"""
        combos = []
        baskets = defaultdict(list)
        
        for (customer, branch), group in self.df.groupby(['customer', 'branch']):
            products = sorted(set(group['product'].tolist()))
            # Limit products per basket to prevent combinatorial explosion
            if len(products) >= 2:
                # Limit to top 10 products per basket to keep it manageable
                if len(products) > 10:
                    # Keep only products with higher prices (more important items)
                    top_products = group.nlargest(10, 'price')['product'].unique().tolist()
                    products = sorted(set(top_products))
                baskets[(customer, branch)] = products
        
        pair_counts = Counter()
        for (customer, branch), products in baskets.items():
            # Generate pairs only for products in this basket
            for pair in combinations(products, 2):
                pair_counts[frozenset(pair)] += 1
        
        min_freq = max(2, int(self.total_transactions * min_support))
        
        for combo_set, frequency in pair_counts.items():
            if frequency >= min_freq:
                products = sorted(list(combo_set))
                support = frequency / self.total_transactions
                
                combos.append({
                    'products': products,
                    'frequency': int(frequency),
                    'support': support,
                    'confidence': support,
                    'lift': None,
                    'avg_revenue': self._get_combo_revenue(products),
                    'ml_generated': False
                })
        
        combos.sort(key=lambda x: (-x['frequency'], -x['avg_revenue']))
        return combos
    
    def _get_combo_revenue(self, products: List[str]) -> float:
        """Calculate average revenue for combo"""
        mask = self.df['product'].isin(products)
        combo_data = self.df[mask]
        return float(combo_data['price'].mean()) if len(combo_data) > 0 else 0.0
    
    def find_combos_by_branch(self, min_support: float = 0.01, max_combos_per_branch: int = 50) -> Dict[str, List[Dict]]:
        """Find combos per branch"""
        result = {}
        branches = [b for b in self.df['branch'].unique() if not pd.isna(b)]
        print(f"   - Processing {len(branches)} branches for branch-specific combos...")
        
        for i, branch in enumerate(branches, 1):
            print(f"     [{i}/{len(branches)}] {branch}...", end="", flush=True)
            branch_df = self.df[self.df['branch'] == branch]
            optimizer = ComboOptimizer(branch_df)
            branch_combos = optimizer.find_combos(min_support=min_support)
            if branch_combos:
                # Limit to top N combos to keep it fast
                result[branch] = branch_combos[:max_combos_per_branch]
                print(f" {len(branch_combos[:max_combos_per_branch])} combos")
            else:
                print(" no combos")
        return result


# Global state for combo analysis
combo_processor = None
combo_optimizer = None
all_combos_cache = None
branch_combos_cache = None

# ═══════════════════════════════════════════════════════════════════════════
# OBJECTIVE 3 & 4: EXPANSION AND STAFFING (CACHED)
# ═══════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def cached_expansion():
    """Cache expansion analysis"""
    return run_expansion_analysis()

@lru_cache(maxsize=1)
def cached_staffing():
    """Cache staffing analysis"""
    return run_staffing_analysis()

@lru_cache(maxsize=1)
def cached_growth_analysis():
    """Cache growth strategy analysis"""
    if not HAS_OBJECTIVE_5:
        return None
    try:
        # Try data folder first, then root
        products_path = Path('data/rep_s_00191_SMRY.csv')
        if not products_path.exists():
            products_path = Path('rep_s_00191_SMRY.csv')
        
        customers_path = Path('data/rep_s_00150.csv')
        if not customers_path.exists():
            customers_path = Path('rep_s_00150.csv')
        
        products_df = load_products_by_division(str(products_path))
        customers_df = load_customers(str(customers_path))
        analysis = CoffeeAndMilkshakeAnalysis(products_df, customers_df)
        analysis.current_state_analysis()
        analysis.customer_segment_analysis()
        analysis.growth_opportunity_analysis()
        analysis.revenue_projection()
        return analysis.insights
    except Exception as e:
        print(f"Growth analysis error: {e}")
        import traceback
        traceback.print_exc()
        return None

# ═══════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def _safe_dict(obj) -> Any:
    """Convert pandas/numpy objects to JSON-serializable types"""
    import pandas as pd
    if isinstance(obj, pd.DataFrame):
        return obj.reset_index().to_dict(orient="records")
    if isinstance(obj, pd.Series):
        return obj.to_dict()
    if isinstance(obj, dict):
        return {k: _safe_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_safe_dict(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, float) and (obj != obj):  # NaN
        return None
    return obj


# ═══════════════════════════════════════════════════════════════════════════
# NATURAL LANGUAGE QUERY ROUTER (OpenClaw Integration)
# ═══════════════════════════════════════════════════════════════════════════

INTENT_PATTERNS = {
    "expansion": [
        r"expand", r"new branch", r"open.*branch", r"feasib",
        r"replicate", r"5th branch", r"location", r"new store"
    ],
    "staffing": [
        r"staff", r"employee", r"shift", r"schedule", r"headcount",
        r"workers?", r"how many people", r"manning"
    ],
    "combos": [
        r"combo", r"combination", r"pair", r"together", r"bundle",
        r"frequently.*bought", r"cross-sell", r"upsell", r"recommend"
    ],
    "growth": [
        r"coffee", r"milkshake", r"beverage", r"drink", r"growth",
        r"increase.*sales", r"boost.*revenue", r"strategy"
    ],
}

KNOWN_BRANCHES = ["Conut - Tyre", "Conut Jnah", "Main Street Coffee", "Conut"]


def detect_intent(query: str) -> tuple:
    """Detect intent and extract branch if mentioned"""
    q = query.lower()
    scores = {}
    for intent, patterns in INTENT_PATTERNS.items():
        scores[intent] = sum(1 for p in patterns if re.search(p, q, re.IGNORECASE))
    
    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        best = "unknown"
    
    # Extract branch
    branch = None
    for b in KNOWN_BRANCHES:
        if b.lower() in q:
            branch = b
            break
    
    return best, branch


# ═══════════════════════════════════════════════════════════════════════════
# STARTUP: LOAD ALL DATA
# ═══════════════════════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup_event():
    """Load all data on startup"""
    global combo_processor, combo_optimizer, all_combos_cache, branch_combos_cache
    
    print("\n" + "="*70)
    print("🚀 CONUT AI OPERATIONS - UNIFIED SYSTEM STARTUP")
    print("="*70)
    
    # Load Objective 1 (Combos)
    print("\n[1/4] Loading Objective 1: Combo Optimization...")
    try:
        combo_processor = ConutDataProcessor(data_dir=".")
        df = combo_processor.load_sales_data()
        print(f"   - Loaded {len(df)} sales records")
        print(f"   - Branches: {df['branch'].unique().tolist()}")
        
        combo_optimizer = ComboOptimizer(df)
        
        # Find global combos - use faster basic method
        print("   - Finding global combos (this may take 10-15 seconds)...")
        all_combos_cache = combo_optimizer.find_combos(min_support=0.03)  # Use basic method, higher threshold
        print(f"   ✓ Global combos: {len(all_combos_cache)} found")
        
        # Skip branch-specific combos for faster startup - generate on-demand via API
        branch_combos_cache = {}
        print(f"   ✓ Branch combos will be generated on-demand")
        
    except Exception as e:
        print(f"   ✗ Combo analysis failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Pre-cache Objective 3 (Expansion)
    print("\n[2/4] Loading Objective 3: Branch Expansion...")
    try:
        expansion_result = cached_expansion()
        print(f"   ✓ Expansion analysis ready (Decision: {expansion_result.get('decision', 'N/A')})")
    except Exception as e:
        print(f"   ✗ Expansion analysis failed: {e}")
    
    # Pre-cache Objective 4 (Staffing)
    print("\n[3/4] Loading Objective 4: Staffing Optimization...")
    try:
        staffing_result = cached_staffing()
        branches = len(staffing_result.get('staffing_recommendations', {}))
        print(f"   ✓ Staffing analysis ready ({branches} branches)")
    except Exception as e:
        print(f"   ✗ Staffing analysis failed: {e}")
    
    # Pre-cache Objective 5 (Growth)
    print("\n[4/4] Loading Objective 5: Growth Strategy...")
    if HAS_OBJECTIVE_5:
        try:
            growth_result = cached_growth_analysis()
            if growth_result:
                print(f"   ✓ Growth strategy ready")
            else:
                print(f"   ✗ Growth strategy returned no data")
        except Exception as e:
            print(f"   ✗ Growth strategy failed: {e}")
    else:
        print("   ⚠ Objective 5 module not available")
    
    print("\n" + "="*70)
    print("✨ ALL SYSTEMS READY - API Available at http://localhost:8000")
    print("📚 Interactive docs at http://localhost:8000/docs")
    print("="*70 + "\n")


# ═══════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    """Root endpoint with system overview"""
    return {
        "service": "Conut AI Chief of Operations",
        "version": "2.0.0",
        "status": "operational",
        "objectives": {
            "1": "Combo Optimization",
            "3": "Branch Expansion Feasibility",
            "4": "Shift Staffing Estimation",
            "5": "Coffee & Milkshake Growth Strategy"
        },
        "endpoints": {
            "natural_language": "/ask?query=<your question>",
            "combos": "/api/combos/*",
            "expansion": "/api/expansion",
            "staffing": "/api/staffing/{branch}",
            "growth": "/api/growth",
            "health": "/health"
        },
        "documentation": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "objectives_loaded": {
            "combos": combo_optimizer is not None,
            "expansion": True,
            "staffing": True,
            "growth": HAS_OBJECTIVE_5
        },
        "combos_found": len(all_combos_cache) if all_combos_cache else 0
    }


# ───────────────────────────────────────────────────────────────────────────
# OBJECTIVE 1: COMBO ENDPOINTS
# ───────────────────────────────────────────────────────────────────────────

@app.get("/api/combos/analysis")
async def get_combo_analysis(
    top_n: int = Query(10, ge=1, le=50),
    min_frequency: int = Query(1, ge=1)
) -> ComboAnalysisResponse:
    """
    Objective 1: Get overall combo analysis
    
    Identifies optimal product combinations based on customer purchasing patterns
    using ML-powered association rule mining (Apriori algorithm).
    """
    if not combo_optimizer or not all_combos_cache:
        raise HTTPException(status_code=503, detail="Combo data not loaded")
    
    filtered = [c for c in all_combos_cache if c['frequency'] >= min_frequency]
    topn = filtered[:top_n]
    
    combo_recommendations = [
        ComboRecommendation(
            combo_id=i,
            products=c['products'],
            frequency=c['frequency'],
            support=round(c['support'], 4),
            avg_revenue=round(c['avg_revenue'], 2),
            confidence=round(c['confidence'], 4),
            lift=round(c['lift'], 4) if c.get('lift') else None,
            ml_generated=c.get('ml_generated', False),
            description=f"{' + '.join(c['products'])} (bought {c['frequency']} times)" +
                       (f" [ML lift: {c['lift']:.2f}]" if c.get('lift') else "")
        )
        for i, c in enumerate(topn)
    ]
    
    return ComboAnalysisResponse(
        total_transactions=combo_optimizer.total_transactions,
        unique_products=len(combo_processor.products),
        total_combos_found=len(filtered),
        top_combos=combo_recommendations,
        by_branch={
            branch: [
                ComboRecommendation(
                    combo_id=i,
                    products=c['products'],
                    frequency=c['frequency'],
                    support=round(c['support'], 4),
                    avg_revenue=round(c['avg_revenue'], 2),
                    confidence=round(c['confidence'], 4),
                    lift=round(c['lift'], 4) if c.get('lift') else None,
                    ml_generated=c.get('ml_generated', False),
                    branch=branch,
                    description=f"{' + '.join(c['products'])} ({c['frequency']} times)"
                )
                for i, c in enumerate(combos[:top_n])
            ]
            for branch, combos in branch_combos_cache.items()
        }
    )


@app.get("/api/combos/top")
async def get_top_combos(
    limit: int = Query(5, ge=1, le=20),
    sort_by: str = Query("frequency", pattern="^(frequency|revenue|support)$")
):
    """Get top N combos sorted by metric"""
    if not all_combos_cache:
        raise HTTPException(status_code=503, detail="Combo data not loaded")
    
    sort_key = {
        'frequency': lambda x: -x['frequency'],
        'revenue': lambda x: -x['avg_revenue'],
        'support': lambda x: -x['support']
    }.get(sort_by, lambda x: -x['frequency'])
    
    sorted_combos = sorted(all_combos_cache, key=sort_key)[:limit]
    
    return {
        "metric": sort_by,
        "ml_enabled": HAS_MLXTEND,
        "combos": [
            {
                "products": c['products'],
                "frequency": c['frequency'],
                "support": round(c['support'], 4),
                "avg_revenue": round(c['avg_revenue'], 2),
                "lift": round(c['lift'], 4) if c.get('lift') else None
            }
            for c in sorted_combos
        ]
    }


@app.get("/api/combos/by-branch/{branch}")
async def get_combos_by_branch(branch: str, limit: int = Query(10, ge=1, le=50)):
    """Get product combos for a specific branch"""
    if not combo_optimizer:
        raise HTTPException(status_code=503, detail="Combo optimizer not loaded")
    
    # Generate branch combos on-demand if not cached
    global branch_combos_cache
    
    # Fuzzy match branch name
    branch_lower = branch.lower()
    matched_branch = None
    
    # Try exact match first
    available_branches = combo_optimizer.df['branch'].unique().tolist()
    for b in available_branches:
        if b.lower() == branch_lower:
            matched_branch = b
            break
    
    # Try partial match if no exact match
    if not matched_branch:
        for b in available_branches:
            if branch_lower in b.lower() or b.lower() in branch_lower:
                matched_branch = b
                break
    
    if not matched_branch:
        raise HTTPException(
            status_code=404, 
            detail=f"No combos for branch: '{branch}'. Available branches: {available_branches}"
        )
    
    # Check if already cached
    if matched_branch not in branch_combos_cache:
        # Generate on-demand
        branch_df = combo_optimizer.df[combo_optimizer.df['branch'] == matched_branch]
        optimizer = ComboOptimizer(branch_df)
        combos = optimizer.find_combos(min_support=0.03)[:50]  # Limit to 50
        branch_combos_cache[matched_branch] = combos
    
    combos = branch_combos_cache[matched_branch][:limit]
    return {
        "branch": matched_branch,
        "query_branch": branch,
        "total_combos": len(branch_combos_cache[matched_branch]),
        "combos": [
            {
                "products": c['products'],
                "frequency": c['frequency'],
                "support": round(c['support'], 4),
                "avg_revenue": round(c['avg_revenue'], 2),
            }
            for c in combos
        ]
    }


# ───────────────────────────────────────────────────────────────────────────
# OBJECTIVE 3: EXPANSION ENDPOINT
# ───────────────────────────────────────────────────────────────────────────

@app.get("/api/expansion")
async def get_expansion_analysis():
    """
    Objective 3: Branch expansion feasibility analysis
    
    Returns GO/CAUTION/NO-GO decision with branch scores and new branch profile.
    """
    try:
        rec = cached_expansion()
        return JSONResponse(content={
            "decision": rec["decision"],
            "confidence": rec["confidence"],
            "best_template_branch": rec["best_template_branch"],
            "justifications": rec["justifications"],
            "risks": rec["risks"],
            "branch_scores": _safe_dict(rec["branch_scores"]),
            "new_branch_profile": _safe_dict(rec["new_branch_profile"]),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ───────────────────────────────────────────────────────────────────────────
# OBJECTIVE 4: STAFFING ENDPOINT
# ───────────────────────────────────────────────────────────────────────────

@app.get("/api/staffing/{branch}")
async def get_staffing_analysis(branch: str):
    """
    Objective 4: Staffing recommendation for a specific branch
    
    Available branches: Conut, Conut - Tyre, Conut Jnah, Main Street Coffee
    """
    try:
        result = cached_staffing()
        rec = result["staffing_recommendations"]
        att_stats = result["attendance_stats"]
        prod = result["productivity_index"]
        
        # Fuzzy branch matching
        branch_lower = branch.lower()
        candidates = []
        for b in rec.keys():
            b_lower = b.lower()
            if b_lower == branch_lower:
                candidates.append((0, b))
            elif branch_lower in b_lower:
                candidates.append((1, b))
            elif b_lower in branch_lower:
                candidates.append((2, b))
        
        candidates.sort(key=lambda x: (x[0], -len(x[1])))
        matched = candidates[0][1] if candidates else None
        
        if not matched:
            raise HTTPException(
                status_code=404,
                detail=f"Branch '{branch}' not found. Available: {list(rec.keys())}"
            )
        
        return JSONResponse(content=_safe_dict({
            "branch": matched,
            "staffing_by_shift": rec.get(matched, {}),
            "attendance_summary": att_stats.loc[[matched]].to_dict(orient="records")[0] if matched in att_stats.index else {},
            "productivity": prod.loc[[matched]].to_dict(orient="records")[0] if matched in prod.index else {},
            "anomalies_count": len(result["anomalies"][
                result["anomalies"]["branch"] == matched
            ]) if not result["anomalies"].empty else 0,
        }))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ───────────────────────────────────────────────────────────────────────────
# OBJECTIVE 5: GROWTH STRATEGY ENDPOINT
# ───────────────────────────────────────────────────────────────────────────

@app.get("/api/growth")
async def get_growth_strategy():
    """
    Objective 5: Coffee & Milkshake growth strategy recommendations
    
    Data-driven strategies to increase beverage sales.
    """
    if not HAS_OBJECTIVE_5:
        raise HTTPException(
            status_code=503,
            detail="Objective 5 module not available. Check dependencies."
        )
    
    try:
        insights = cached_growth_analysis()
        if not insights:
            raise HTTPException(status_code=500, detail="Growth analysis returned no data")
        
        response = growth_recommendations_endpoint(insights)
        return JSONResponse(content=_safe_dict(response))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Growth analysis error: {e}")


# ───────────────────────────────────────────────────────────────────────────
# NATURAL LANGUAGE ENDPOINT (OpenClaw Integration)
# ───────────────────────────────────────────────────────────────────────────

@app.get("/ask")
async def ask_natural_language(query: str = Query(..., description="Natural language query")):
    """
    Natural language query dispatcher for OpenClaw integration
    
    Examples:
    - "Should we open a new branch?"
    - "How many staff do we need at Conut Jnah evening shift?"
    - "What products are frequently bought together?"
    - "How can we increase coffee sales?"
    """
    intent, branch = detect_intent(query)
    
    try:
        if intent == "expansion":
            rec = cached_expansion()
            return JSONResponse(content={
                "query": query,
                "intent": "expansion",
                "objective": 3,
                "decision": rec["decision"],
                "confidence": rec["confidence"],
                "best_template_branch": rec["best_template_branch"],
                "justifications": rec["justifications"],
                "recommendation": f"Decision: {rec['decision']}. Best model: {rec['best_template_branch']}"
            })
        
        elif intent == "staffing":
            target_branch = branch or "Conut Jnah"
            result = await get_staffing_analysis(target_branch)
            data = _safe_dict(result.body) if hasattr(result, 'body') else result
            return JSONResponse(content={
                "query": query,
                "intent": "staffing",
                "objective": 4,
                **data
            })
        
        elif intent == "combos":
            combos = all_combos_cache[:5] if all_combos_cache else []
            return JSONResponse(content={
                "query": query,
                "intent": "combos",
                "objective": 1,
                "top_combos": [
                    {
                        "products": c['products'],
                        "frequency": c['frequency'],
                        "recommendation": f"Bundle {' + '.join(c['products'])}"
                    }
                    for c in combos
                ],
                "recommendation": f"Top combo: {' + '.join(combos[0]['products'])}" if combos else "No combos found"
            })
        
        elif intent == "growth":
            if not HAS_OBJECTIVE_5:
                return JSONResponse(content={
                    "query": query,
                    "intent": "growth",
                    "objective": 5,
                    "error": "Growth strategy module not available"
                })
            insights = cached_growth_analysis()
            if insights:
                return JSONResponse(content={
                    "query": query,
                    "intent": "growth",
                    "objective": 5,
                    "current_state": insights.get('current_state', {}),
                    "top_opportunities": insights.get('opportunities', [])[:3],
                    "recommendation": insights['opportunities'][0]['name'] if insights.get('opportunities') else "No recommendations"
                })
        
        return JSONResponse(content={
            "query": query,
            "intent": "unknown",
            "message": "Query not understood. Try asking about: expansion, staffing, combos, or growth strategy.",
            "available_endpoints": {
                "expansion": "/api/expansion",
                "staffing": "/api/staffing/{branch}",
                "combos": "/api/combos/analysis",
                "growth": "/api/growth"
            }
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN RUNNER
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n🚀 Starting Conut AI Unified Operations System...")
    print("📍 Server will be available at: http://localhost:8000")
    print("📚 API Documentation: http://localhost:8000/docs\n")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
