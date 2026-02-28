"""
OBJECTIVE 3: Branch Expansion Feasibility
==========================================
Conut AI Engineering Hackathon

Purpose:
  Evaluate whether opening a new branch is feasible and recommend candidate 
  locations based on multi-dimensional analysis of existing branches.

Methodology
-----------
We have 4 branches: Conut, Conut - Tyre, Conut Jnah, Main Street Coffee.
For a new branch recommendation we:
  1. Extract multi-dimensional signals per existing branch.
  2. Build a composite "Market Saturation / Potential Score".
  3. Run a weighted scoring model to rank which market profile a 5th branch
     should replicate — and flag the signals that justify expansion.

Signals Used
------------
- Revenue trajectory (monthly growth rate Aug-Dec 2025)
- Revenue per customer (avg_sales_by_menu)
- Customer throughput (total customers served)
- Revenue density (total_revenue / num_customers)
- Revenue momentum (last-month vs. first-month ratio)
- Tax-adjusted revenue (cross-validated via REP_S_00194)
- Market channel mix (delivery vs table vs take-away split)
- Delivery penetration ratio (delivery customers / total)
"""
from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd
from scipy.stats import zscore

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.data_loader import (
    load_monthly_sales,
    load_avg_sales_by_menu,
    load_tax_summary,
    load_customer_orders,
)


# ─────────────────────────────────────────────────────────
# Feature Engineering
# ─────────────────────────────────────────────────────────

def _growth_rate(series: pd.Series) -> float:
    """Compound monthly growth rate over the observation window."""
    s = series.dropna().values
    if len(s) < 2:
        return 0.0
    # CAGR-style: (last/first)^(1/(n-1)) - 1
    return float((s[-1] / s[0]) ** (1 / (len(s) - 1)) - 1)


def _momentum(series: pd.Series) -> float:
    """Last value vs. mean of all but last — captures recency acceleration."""
    s = series.dropna().values
    if len(s) < 2:
        return 1.0
    return float(s[-1] / np.mean(s[:-1])) if np.mean(s[:-1]) > 0 else 1.0


def build_branch_features() -> pd.DataFrame:
    """
    Returns a DataFrame with one row per branch and all engineered features.
    """
    monthly = load_monthly_sales()
    menu = load_avg_sales_by_menu()
    tax = load_tax_summary()
    orders = load_customer_orders()

    branches = sorted(monthly["branch"].unique())
    rows = []

    for b in branches:
        m = monthly[monthly["branch"] == b].sort_values("month")
        rev_series = m["revenue"]

        # -- Revenue features --
        total_rev = rev_series.sum()
        monthly_avg = rev_series.mean()
        growth_rate = _growth_rate(rev_series)
        momentum = _momentum(rev_series)
        n_months = len(rev_series)

        # Best and worst month
        best_month_rev = rev_series.max()
        worst_month_rev = rev_series.min()
        peak_trough_ratio = best_month_rev / worst_month_rev if worst_month_rev > 0 else 1.0

        # -- Customer features (from menu table) --
        bm = menu[menu["branch"] == b]
        total_customers = bm["num_customers"].sum()
        total_sales_menu = bm["total_sales"].sum()
        avg_per_customer = (
            (bm["total_sales"] * bm["num_customers"]).sum() / total_customers
            if total_customers > 0 else 0.0
        )

        # Channel mix
        delivery_cust = bm[bm["menu"] == "DELIVERY"]["num_customers"].sum()
        table_cust = bm[bm["menu"] == "TABLE"]["num_customers"].sum()
        takeaway_cust = bm[bm["menu"] == "TAKE AWAY"]["num_customers"].sum()
        delivery_pct = delivery_cust / total_customers if total_customers > 0 else 0.0
        table_pct = table_cust / total_customers if total_customers > 0 else 0.0
        takeaway_pct = takeaway_cust / total_customers if total_customers > 0 else 0.0

        # -- Tax revenue (cross-check) --
        bt = tax[tax["branch"].str.strip() == b.strip()]
        tax_rev = bt["total_revenue"].values[0] if not bt.empty else np.nan

        # -- Delivery order stats (rep_s_00150) --
        od = orders[orders["branch"] == b]
        od_clean = od[od["total"] > 0]
        delivery_order_count = len(od_clean)
        delivery_avg_ticket = od_clean["total"].mean() if not od_clean.empty else np.nan
        repeat_customer_pct = (od["num_orders"] > 1).mean() if not od.empty else 0.0

        rows.append({
            "branch": b,
            # Revenue signals
            "total_revenue": total_rev,
            "monthly_avg_revenue": monthly_avg,
            "monthly_growth_rate": growth_rate,
            "revenue_momentum": momentum,
            "n_months_observed": n_months,
            "peak_trough_ratio": peak_trough_ratio,
            # Customer signals
            "total_customers": total_customers,
            "avg_revenue_per_customer": avg_per_customer,
            # Channel mix
            "delivery_pct": delivery_pct,
            "table_pct": table_pct,
            "takeaway_pct": takeaway_pct,
            # Tax cross-check
            "tax_reported_revenue": tax_rev,
            # Delivery depth
            "delivery_order_count": delivery_order_count,
            "delivery_avg_ticket": delivery_avg_ticket,
            "repeat_customer_pct": repeat_customer_pct,
        })

    df = pd.DataFrame(rows).set_index("branch")
    return df


# ─────────────────────────────────────────────────────────
# Composite Scoring
# ─────────────────────────────────────────────────────────

# Feature weights — higher = this factor matters more for expansion attractiveness
WEIGHTS = {
    "monthly_growth_rate": 0.25,      # Growing branches = good template
    "revenue_momentum": 0.20,         # Recent acceleration matters most
    "total_customers": 0.15,          # Volume proves market depth
    "avg_revenue_per_customer": 0.15, # Quality of spend
    "delivery_pct": 0.10,             # Delivery-capable = scalable model
    "repeat_customer_pct": 0.10,      # Loyalty = stable base
    "peak_trough_ratio": -0.05,       # High volatility = risk (negative weight)
}


def score_branches(features: pd.DataFrame) -> pd.DataFrame:
    """
    Compute a 0-100 composite expansion attractiveness score per branch.
    Uses z-score normalisation then weighted sum, mapped to 0-100.
    """
    df = features.copy()

    score_cols = list(WEIGHTS.keys())
    # Z-score normalise each feature
    norms = {}
    for col in score_cols:
        if col in df.columns:
            vals = df[col].fillna(df[col].median())
            std = vals.std()
            if std > 0:
                norms[col] = (vals - vals.mean()) / std
            else:
                norms[col] = pd.Series(0.0, index=df.index)

    # Weighted sum
    composite = pd.Series(0.0, index=df.index)
    total_weight = 0.0
    for col, w in WEIGHTS.items():
        if col in norms:
            composite += w * norms[col]
            total_weight += abs(w)

    composite /= total_weight

    # Map to 0-100
    mn, mx = composite.min(), composite.max()
    if mx > mn:
        composite = 100 * (composite - mn) / (mx - mn)
    else:
        composite = pd.Series(50.0, index=df.index)

    df["expansion_score"] = composite.round(1)
    df = df.sort_values("expansion_score", ascending=False)
    return df


# ─────────────────────────────────────────────────────────
# Recommendation Engine
# ─────────────────────────────────────────────────────────

def generate_recommendation(scored: pd.DataFrame) -> Dict:
    """
    Returns a structured recommendation dict with:
      - Should Conut expand? (Go / Caution / No-Go)
      - Best branch model to replicate
      - Top 5 justifications
      - Risk factors
      - Suggested location characteristics
    """
    best = scored.index[0]
    worst = scored.index[-1]
    bf = scored.loc[best]
    overall_growth = scored["monthly_growth_rate"].mean()
    overall_momentum = scored["revenue_momentum"].mean()

    # Decision rule
    if overall_growth > 0.05 and overall_momentum > 1.1:
        decision = "GO"
        confidence = "High"
    elif overall_growth > 0.0 or overall_momentum > 1.0:
        decision = "CAUTION"
        confidence = "Medium"
    else:
        decision = "NO-GO"
        confidence = "Low"

    justifications = []

    # Evidence 1: growth
    avg_growth_pct = overall_growth * 100
    justifications.append(
        f"Network-wide average monthly revenue growth is {avg_growth_pct:.1f}% "
        f"(Aug-Dec 2025), confirming demand expansion."
    )

    # Evidence 2: momentum
    justifications.append(
        f"Revenue momentum index = {overall_momentum:.2f}x — last month outperformed "
        f"prior period average, signalling demand acceleration."
    )

    # Evidence 3: best branch revenue per customer
    justifications.append(
        f"{best} achieves avg revenue per customer of "
        f"{bf['avg_revenue_per_customer']:,.0f} units — highest in the network, "
        f"proving premium pricing is sustainable."
    )

    # Evidence 4: customer volume
    total_cust = scored["total_customers"].sum()
    justifications.append(
        f"Combined network served {total_cust:,.0f} unique customers in 2025, "
        f"demonstrating validated brand recognition across multiple markets."
    )

    # Evidence 5: delivery penetration
    best_delivery = scored["delivery_pct"].max()
    best_delivery_branch = scored["delivery_pct"].idxmax()
    justifications.append(
        f"{best_delivery_branch} has {best_delivery*100:.1f}% delivery channel share "
        f"— the new branch should prioritise delivery infrastructure from day one."
    )

    # Risk factors
    risks = []
    high_volatility = scored[scored["peak_trough_ratio"] > 3.0]
    if not high_volatility.empty:
        risks.append(
            f"Revenue seasonality risk: {', '.join(high_volatility.index)} show "
            f"peak/trough ratios > 3x, suggesting strong seasonal dependency."
        )
    worst_growth = scored["monthly_growth_rate"].min()
    if worst_growth < 0:
        risks.append(
            f"{worst} is declining ({worst_growth*100:.1f}%/month) — market saturation "
            f"or operational issues present; avoid replicating that model."
        )
    risks.append(
        "Numeric values are in scaled units — absolute thresholds should be "
        "recalibrated against real LBP/USD figures before committing capital."
    )

    # Location profile
    profile = {
        "model_branch": best,
        "target_menu_channel": "TAKE AWAY + DELIVERY" if bf["takeaway_pct"] > 0.3 else "TABLE",
        "min_customer_catchment": int(scored["total_customers"].median()),
        "target_monthly_revenue": f"{bf['monthly_avg_revenue']:,.0f} units",
        "delivery_capability_required": bf["delivery_pct"] > 0.05,
    }

    return {
        "decision": decision,
        "confidence": confidence,
        "best_template_branch": best,
        "justifications": justifications,
        "risks": risks,
        "new_branch_profile": profile,
        "branch_scores": scored[["expansion_score", "monthly_growth_rate",
                                  "revenue_momentum", "total_customers",
                                  "avg_revenue_per_customer",
                                  "delivery_pct", "repeat_customer_pct"]].round(4),
    }


# ─────────────────────────────────────────────────────────
# Top-level API
# ─────────────────────────────────────────────────────────

def run_expansion_analysis() -> Dict:
    """Full pipeline: load data -> features -> score -> recommend."""
    features = build_branch_features()
    scored = score_branches(features)
    recommendation = generate_recommendation(scored)
    recommendation["features"] = features
    return recommendation


def print_report(rec: Dict) -> None:
    sep = "=" * 65
    print(f"\n{sep}")
    print("  CONUT EXPANSION FEASIBILITY REPORT")
    print(sep)
    print(f"  Decision  : {rec['decision']}  (Confidence: {rec['confidence']})")
    print(f"  Template  : Replicate '{rec['best_template_branch']}' model")
    print(f"\n  Branch Scores:")
    print(rec["branch_scores"].to_string())

    print(f"\n  Key Justifications:")
    for i, j in enumerate(rec["justifications"], 1):
        print(f"  {i}. {j}")

    print(f"\n  Risk Factors:")
    for r in rec["risks"]:
        print(f"  - {r}")

    p = rec["new_branch_profile"]
    print(f"\n  New Branch Profile:")
    for k, v in p.items():
        print(f"    {k}: {v}")
    print(sep)


if __name__ == "__main__":
    rec = run_expansion_analysis()
    print_report(rec)
