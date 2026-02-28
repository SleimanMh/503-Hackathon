"""
OBJECTIVE 1: Combo Optimization
================================
Conut AI Engineering Hackathon

Purpose:
  Identify optimal product combinations based on customer purchasing patterns.
  
Implementation:
  - Uses ML-based association rule mining (Apriori algorithm)
  - Analyzes real customer transaction data from REP_S_00502.csv
  - Calculates support, confidence, and lift metrics
  - Provides branch-specific recommendations
  
API Endpoints:
  - GET /api/combos/analysis - Full combo analysis
  - GET /api/combos/top - Top N combos by metric
  - GET /api/combos/by-branch/{branch} - Branch-specific combos
  - POST /api/combos/recommend - Product pairing recommendations
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from pydantic import BaseModel
import re
from collections import defaultdict, Counter
from itertools import combinations
import json
import csv
from io import StringIO

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# ML libraries for association rule mining
try:
    from mlxtend.frequent_patterns import apriori, association_rules
    from mlxtend.preprocessing import TransactionEncoder
    HAS_MLXTEND = True
except ImportError:
    HAS_MLXTEND = False
    print("Warning: mlxtend not installed. Using basic frequency analysis.")

# Initialize FastAPI app
app = FastAPI(
    title="Conut Chief of Operations Agent",
    description="AI-driven decision support for Conut operations",
    version="1.0.0"
)

# Add CORS middleware for OpenClaw integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DATA MODELS

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


# DATA LOADING AND CLEANING

class ConutDataProcessor:
    """Handles loading, cleaning, and processing Conut sales data"""
    
    def __init__(self, data_dir: str = "."):
        self.data_dir = Path(data_dir)
        self.transactions = []
        self.products = set()
        
    def load_sales_data(self, filename: str = "REP_S_00502.csv") -> pd.DataFrame:
        """
        Load and clean the sales by customer details CSV.
        This file has a messy report format with branch markers and page headers.
        """
        filepath = self.data_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        # Read the raw file
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Parse using CSV reader to handle quoted fields properly
        records = []
        current_branch = None
        current_customer = None
        
        for line_raw in lines:
            line_raw = line_raw.rstrip('\n')
            
            # Skip empty lines
            if not line_raw.strip():
                continue
            
            # Detect branch marker (format: "Branch :Conut - Tyre,,,,")
            if "Branch :" in line_raw and not line_raw.startswith(","):
                parts = line_raw.split(",")
                if parts[0].startswith("Branch :"):
                    current_branch = parts[0].replace("Branch :", "").strip()
                continue
            
            # Skip report headers and metadata
            skip_keywords = ["Sales by customer", "Page", "From Date:", "To Date:", 
                           "Full Name,", "Total :", "Total by Branch"]
            if any(k in line_raw for k in skip_keywords):
                continue
            
            # Detect customer ID (at start of line, before commas, with "Person_")
            first_field = line_raw.split(",")[0].strip()
            if first_field and "Person_" in first_field and not line_raw.startswith(","):
                current_customer = first_field
                continue
            
            # Parse item lines (start with comma)
            if line_raw.startswith(",") and current_customer and current_branch:
                try:
                    # Use csv reader for proper quote handling
                    reader = csv.reader(StringIO(line_raw))
                    row = next(reader)
                    
                    if len(row) >= 4:
                        qty_str = row[1].strip() if len(row) > 1 else ""
                        desc_raw = row[2].strip() if len(row) > 2 else ""
                        price_str = row[3].strip() if len(row) > 3 else ""
                        
                        # Skip if empty desc
                        if not desc_raw:
                            continue
                        
                        # Parse quantity
                        try:
                            qty = float(qty_str)
                        except:
                            continue
                        
                        # Skip zero-qty items
                        if qty == 0:
                            continue
                        
                        # Parse price
                        price_clean = price_str.replace(",", "")
                        try:
                            price = float(price_clean) if price_clean else 0
                        except:
                            price = 0
                        
                        # Skip zero-price or negative items (refunds), and delivery charges
                        if price <= 0 or "DELIVERY CHARGE" in desc_raw.upper():
                            continue
                        
                        # Normalize description: remove parentheses content and trailing dots
                        desc = re.sub(r'\s*\([^)]*\)|\s*\.$', '', desc_raw).strip()
                        
                        if desc:  # Only add valid products
                            records.append({
                                'customer': current_customer,
                                'branch': current_branch,
                                'product': desc,
                                'qty': abs(qty),
                                'price': abs(price)
                            })
                            self.products.add(desc)
                
                except Exception as e:
                    continue
        
        df = pd.DataFrame(records) if records else pd.DataFrame(columns=['customer', 'branch', 'product', 'qty', 'price'])
        return df
    
    def get_customer_baskets(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """
        Aggregate items by customer to get market baskets.
        Returns dict mapping (customer, branch) -> list of products
        """
        baskets = {}
        for (customer, branch), group in df.groupby(['customer', 'branch']):
            products = group['product'].tolist()
            baskets[(customer, branch)] = products
        return baskets
    
    def get_transaction_pairs(self, df: pd.DataFrame) -> Dict[str, int]:
        """
        Find all product pairs (combos) and their frequency.
        Returns dict mapping frozenset of products -> frequency
        """
        pairs = Counter()
        
        for (customer, branch), group in df.groupby(['customer', 'branch']):
            products = group['product'].unique().tolist()
            
            # Find all pairs in this transaction
            if len(products) >= 2:
                for pair in combinations(sorted(set(products)), 2):
                    pairs[frozenset(pair)] += 1
        
        return pairs


# COMBO OPTIMIZATION ENGINE

class ComboOptimizer:
    """Analyzes product combinations and identifies optimal combos using ML"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.total_transactions = len(df.groupby(['customer', 'branch']))
        self.total_items = len(df)
        self.ml_rules = None  # Store ML-generated association rules
        
    def calculate_support(self, products: frozenset, basket_count: int) -> float:
        """Support: fraction of baskets containing all products in combo"""
        return basket_count / self.total_transactions if self.total_transactions > 0 else 0
    
    def calculate_confidence(self, products: frozenset, basket_count: int) -> float:
        """Confidence: likelihood of buying all items together"""
        return self.calculate_support(products, basket_count)
    
    def find_combos_ml(self, min_support: float = 0.02, min_confidence: float = 0.3) -> List[Dict]:
        """
        ML-based combo discovery using Apriori algorithm and association rules.
        
        Args:
            min_support: minimum support for Apriori
            min_confidence: minimum confidence for association rules
        
        Returns:
            List of combo dicts with ML metrics (support, confidence, lift)
        """
        if not HAS_MLXTEND:
            return self.find_combos(min_support=min_support)
        
        # Prepare transaction data for ML
        transactions = []
        for (customer, branch), group in self.df.groupby(['customer', 'branch']):
            products = group['product'].tolist()
            transactions.append(products)
        
        if not transactions:
            return []
        
        # Convert to one-hot encoded DataFrame for Apriori
        te = TransactionEncoder()
        te_ary = te.fit(transactions).transform(transactions)
        df_encoded = pd.DataFrame(te_ary, columns=te.columns_)
        
        # Apply Apriori algorithm (ML-based frequent pattern mining)
        try:
            frequent_itemsets = apriori(df_encoded, min_support=min_support, use_colnames=True)
            
            if len(frequent_itemsets) == 0:
                return []
            
            # Generate association rules with ML metrics
            rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=min_confidence, num_itemsets=len(frequent_itemsets))
            self.ml_rules = rules
            
            # Convert rules to combo format
            combos = []
            for idx, rule in rules.iterrows():
                # Combine antecedent and consequent
                products = list(rule['antecedents']) + list(rule['consequents'])
                products_list = sorted(products)
                
                # Calculate frequency from support
                frequency = int(rule['support'] * self.total_transactions)
                
                # Get average revenue
                combo_revenue = self._get_combo_revenue(products_list)
                
                combos.append({
                    'products': products_list,
                    'frequency': frequency,
                    'support': float(rule['support']),
                    'confidence': float(rule['confidence']),
                    'lift': float(rule['lift']),
                    'avg_revenue': combo_revenue,
                    'ml_generated': True
                })
            
            # Remove duplicates and sort by lift (ML relevance metric)
            seen = set()
            unique_combos = []
            for combo in combos:
                key = frozenset(combo['products'])
                if key not in seen:
                    seen.add(key)
                    unique_combos.append(combo)
            
            unique_combos.sort(key=lambda x: (-x['lift'], -x['confidence'], -x['frequency']))
            return unique_combos
            
        except Exception as e:
            print(f"ML algorithm failed: {e}. Falling back to basic method.")
            return self.find_combos(min_support=min_support)
    
    def find_combos(self, min_support: float = 0.02, min_frequency: int = 2) -> List[Dict]:
        """
        Find product combinations meeting min thresholds.
        
        Args:
            min_support: minimum support (% of all transactions)
            min_frequency: minimum number of occurrences
        
        Returns:
            List of combo dicts with metrics
        """
        combos = []
        seen_pairs = set()
        
        # Get all customer baskets
        baskets = defaultdict(list)
        for (customer, branch), group in self.df.groupby(['customer', 'branch']):
            products = sorted(set(group['product'].tolist()))
            if len(products) >= 2:
                baskets[(customer, branch)] = products
        
        # Find all pairs and higher-order combos
        for (customer, branch), products in baskets.items():
            # 2-item combos
            for pair in combinations(products, 2):
                pair_key = frozenset(pair)
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
        
        # Count frequencies
        pair_counts = Counter()
        for (customer, branch), products in baskets.items():
            for pair in combinations(sorted(set(products)), 2):
                pair_counts[frozenset(pair)] += 1
        
        # Filter by thresholds
        min_freq = max(min_frequency, int(self.total_transactions * min_support))
        
        for combo_set, frequency in pair_counts.items():
            if frequency >= min_freq:
                products_list = sorted(list(combo_set))
                
                # Calculate average revenue for this combo
                combo_revenue = self._get_combo_revenue(products_list)
                
                combos.append({
                    'products': products_list,
                    'frequency': int(frequency),
                    'support': self.calculate_support(combo_set, frequency),
                    'confidence': self.calculate_confidence(combo_set, frequency),
                    'lift': None,
                    'avg_revenue': combo_revenue,
                    'ml_generated': False
                })
        
        # Sort by frequency then revenue
        combos.sort(key=lambda x: (-x['frequency'], -x['avg_revenue']))
        return combos
    
    def _get_combo_revenue(self, products: List[str]) -> float:
        """Calculate average revenue for a combo"""
        mask = self.df['product'].isin(products)
        combo_data = self.df[mask]
        
        if len(combo_data) == 0:
            return 0.0
        
        # Average price per item in combo
        return float(combo_data['price'].mean())
    
    def find_combos_by_branch(self, min_support: float = 0.02) -> Dict[str, List[Dict]]:
        """Find combos segmented by branch"""
        result = {}
        
        for branch in self.df['branch'].unique():
            if pd.isna(branch):
                continue
            
            branch_df = self.df[self.df['branch'] == branch]
            optimizer = ComboOptimizer(branch_df)
            branch_combos = optimizer.find_combos(min_support=min_support)
            
            if branch_combos:
                result[branch] = branch_combos
        
        return result


# GLOBAL STATE

processor = None
optimizer = None
all_combos = None
branch_combos = None

def load_all_data():
    """Load and process all data once on startup"""
    global processor, optimizer, all_combos, branch_combos
    
    try:
        processor = ConutDataProcessor(data_dir=".")
        df = processor.load_sales_data()
        
        if len(df) == 0:
            raise ValueError("No data loaded from CSV")
        
        optimizer = ComboOptimizer(df)
        # Use ML-based combo discovery (Apriori algorithm)
        all_combos = optimizer.find_combos_ml(min_support=0.01, min_confidence=0.1)
        branch_combos = optimizer.find_combos_by_branch(min_support=0.01)
        
        return True
    except Exception as e:
        print(f"Error loading data: {e}")
        return False


# FASTAPI ENDPOINTS

@app.on_event("startup")
async def startup_event():
    """Load data on app startup"""
    success = load_all_data()
    if success:
        print("✓ Data loaded successfully")
    else:
        print("✗ Failed to load data")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "data_loaded": optimizer is not None,
        "combos_found": len(all_combos) if all_combos else 0
    }


@app.get("/api/combos/analysis")
async def get_combo_analysis(
    top_n: int = Query(10, ge=1, le=50),
    min_frequency: int = Query(1, ge=1)
) -> ComboAnalysisResponse:
    """
    Get overall combo analysis.
    
    Objective 1: Identify optimal product combinations based on customer purchasing patterns.
    
    Query Parameters:
    - top_n: Number of top combos to return (default: 10)
    - min_frequency: Minimum number of times combo appears (default: 1)
    """
    if not optimizer or not all_combos:
        raise HTTPException(status_code=503, detail="Data not loaded")
    
    # Filter by frequency
    filtered = [c for c in all_combos if c['frequency'] >= min_frequency]
    topn = filtered[:top_n]
    
    # Format response
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
        total_transactions=optimizer.total_transactions,
        unique_products=len(processor.products),
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
            for branch, combos in branch_combos.items()
        }
    )


@app.get("/api/combos/top")
async def get_top_combos(
    limit: int = Query(5, ge=1, le=20),
    sort_by: str = Query("frequency", pattern="^(frequency|revenue|support)$")
) -> Dict:
    """
    Get top N combos sorted by specified metric.
    
    - frequency: Most frequently bought together
    - revenue: Highest average transaction value
    - support: Highest percentage of all transactions
    """
    if not all_combos:
        raise HTTPException(status_code=503, detail="Data not loaded")
    
    # Sort by requested metric
    sort_key = {
        'frequency': lambda x: -x['frequency'],
        'revenue': lambda x: -x['avg_revenue'],
        'support': lambda x: -x['support']
    }.get(sort_by, lambda x: -x['frequency'])
    
    sorted_combos = sorted(all_combos, key=sort_key)[:limit]
    
    return {
        "metric": sort_by,
        "ml_enabled": HAS_MLXTEND,
        "combos": [
            {
                "products": c['products'],
                "frequency": c['frequency'],
                "support": round(c['support'], 4),
                "avg_revenue": round(c['avg_revenue'], 2),
                "confidence": round(c['confidence'], 4),
                "lift": round(c['lift'], 4) if c.get('lift') else None,
                "ml_generated": c.get('ml_generated', False)
            }
            for c in sorted_combos
        ]
    }


@app.get("/api/combos/by-branch/{branch}")
async def get_combos_by_branch(
    branch: str,
    limit: int = Query(10, ge=1, le=50)
) -> Dict:
    """
    Get product combos for a specific branch.
    
    Useful for localized inventory and staffing decisions.
    """
    if not branch_combos or branch not in branch_combos:
        raise HTTPException(
            status_code=404,
            detail=f"No combos found for branch: {branch}"
        )
    
    combos = branch_combos[branch][:limit]
    
    return {
        "branch": branch,
        "total_combos": len(branch_combos[branch]),
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


@app.post("/api/combos/recommend")
async def get_combo_recommendation(
    product: str,
    branch: Optional[str] = None
) -> Dict:
    """
    Given a product, recommend what else customers typically buy with it.
    
    Useful for:
    - Sales staff recommendations
    - Upselling strategies
    - Menu placement decisions
    """
    if not all_combos:
        raise HTTPException(status_code=503, detail="Data not loaded")
    
    # Find combos containing this product
    matching_combos = [
        c for c in all_combos
        if any(product.lower() in p.lower() for p in c['products'])
    ]
    
    if not matching_combos:
        raise HTTPException(
            status_code=404,
            detail=f"No combos found for product: {product}"
        )
    
    # Get co-occurring products
    cooccurring = Counter()
    for combo in matching_combos:
        for p in combo['products']:
            if product.lower() not in p.lower():
                cooccurring[p] += combo['frequency']
    
    top_pairs = cooccurring.most_common(5)
    
    return {
        "product": product,
        "frequently_bought_with": [
            {
                "product": p[0],
                "frequency": p[1]
            }
            for p in top_pairs
        ],
        "recommendation": f"Customers buying '{product}' also frequently buy: {', '.join([p[0] for p in top_pairs])}"
    }


@app.get("/api/products")
async def get_all_products() -> Dict:
    """Get list of all products in the system"""
    if not processor:
        raise HTTPException(status_code=503, detail="Data not loaded")
    
    return {
        "total_unique_products": len(processor.products),
        "products": sorted(list(processor.products))
    }


@app.get("/api/stats/summary")
async def get_summary_stats() -> Dict:
    """Get high-level statistics about the dataset"""
    if not optimizer or not all_combos:
        raise HTTPException(status_code=503, detail="Data not loaded")
    
    all_frequencies = [c['frequency'] for c in all_combos]
    all_revenues = [c['avg_revenue'] for c in all_combos]
    
    return {
        "total_transactions": optimizer.total_transactions,
        "unique_products": len(processor.products),
        "total_product_items": optimizer.total_items,
        "combos_discovered": len(all_combos),
        "avg_combo_frequency": round(np.mean(all_frequencies), 2) if all_frequencies else 0,
        "avg_combo_revenue": round(np.mean(all_revenues), 2) if all_revenues else 0,
        "branches": sorted(list(set(branch_combos.keys()))),
        "highest_frequency_combo": {
            "products": all_combos[0]['products'],
            "frequency": all_combos[0]['frequency']
        } if all_combos else None
    }


# ROOT ENDPOINT

@app.get("/")
async def root():
    """Root endpoint with API documentation"""
    return {
        "message": "Conut Chief of Operations Agent",
        "objective": "1. Combo Optimization - Identify optimal product combinations",
        "endpoints": {
            "health": "/health",
            "combo_analysis": "/api/combos/analysis",
            "top_combos": "/api/combos/top",
            "branch_combos": "/api/combos/by-branch/{branch}",
            "recommend": "/api/combos/recommend?product=<product_name>",
            "all_products": "/api/products",
            "stats": "/api/stats/summary"
        },
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
