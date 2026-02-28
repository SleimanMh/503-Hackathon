"""
coffee_milkshake_engine.py
==========================
Coffee & Milkshake Growth Strategy for Conut.

Methodology
-----------
Uses rep_s_00191_SMRY.csv (Sales by Items by Group) which contains
per-branch item-level revenue and quantities for all of 2025.

Analysis pipeline:
1. Revenue breakdown by division (Hot-Coffee, Frappes, Shakes, etc.)
2. Pareto analysis — which 20% of SKUs drive 80% of beverage revenue?
3. Top performers vs. under-performers within each category
4. Cross-branch comparison — which branch is best at each category?
5. Price-elasticity proxy — revenue per unit by SKU
6. Growth opportunity matrix — high potential / low current volume
7. Actionable recommendations: feature items, bundle ideas, pricing gaps

Divisions in scope:
  - Hot-Coffee Based
  - Frappes
  - Shakes
  - Hot and Cold Drinks (secondary)
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.data_loader import load_items_sales

# ─────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────

BEVERAGE_DIVISIONS = {
    "Hot-Coffee Based": "coffee",
    "Frappes": "frappe",
    "Shakes": "milkshake",
    "Hot and Cold Drinks": "cold_drink",
}

# Items to exclude from strategy (infrastructure / modifiers)
EXCLUDE_ITEMS = {
    "WATER", "DELIVERY CHARGE", "SEND CUTLERY", "DONT SEND CUTLERY",
    "TAKE AWAY",
}


# ─────────────────────────────────────────────────────────
# Data Preparation
# ─────────────────────────────────────────────────────────

def load_beverage_data() -> pd.DataFrame:
    """
    Load items sales and filter to beverage divisions only.
    Returns enriched DataFrame with category, revenue_per_unit columns.
    """
    items = load_items_sales()
    if items.empty:
        return pd.DataFrame()

    # Map division to category
    items["category"] = items["division"].map(BEVERAGE_DIVISIONS)
    bev = items[items["category"].notna()].copy()

    # Exclude noise items
    bev = bev[~bev["item"].str.upper().isin(EXCLUDE_ITEMS)]

    # Revenue per unit
    bev["revenue_per_unit"] = bev.apply(
        lambda r: r["revenue"] / r["qty"] if r["qty"] > 0 else np.nan, axis=1
    )

    return bev.reset_index(drop=True)


# ─────────────────────────────────────────────────────────
# Pareto Analysis
# ─────────────────────────────────────────────────────────

def pareto_analysis(bev_df: pd.DataFrame, category: str = None) -> pd.DataFrame:
    """
    Compute cumulative revenue share (Pareto curve) for beverage items.
    If category provided, filter to that category first.
    """
    df = bev_df.copy()
    if category:
        df = df[df["category"] == category]
    if df.empty:
        return pd.DataFrame()

    agg = (
        df.groupby("item")
        .agg(total_revenue=("revenue", "sum"), total_qty=("qty", "sum"))
        .sort_values("total_revenue", ascending=False)
        .reset_index()
    )
    agg["rev_share_pct"] = (agg["total_revenue"] / agg["total_revenue"].sum() * 100).round(2)
    agg["cumulative_pct"] = agg["rev_share_pct"].cumsum().round(2)
    agg["is_top_20pct"] = agg["cumulative_pct"] <= 80.0
    agg["revenue_per_unit"] = (agg["total_revenue"] / agg["total_qty"].replace(0, np.nan)).round(0)
    return agg


# ─────────────────────────────────────────────────────────
# Cross-Branch Comparison
# ─────────────────────────────────────────────────────────

def cross_branch_category_revenue(bev_df: pd.DataFrame) -> pd.DataFrame:
    """
    Per-branch revenue breakdown by category.
    """
    pivot = (
        bev_df.groupby(["branch", "category"])["revenue"]
        .sum()
        .unstack(fill_value=0)
        .round(0)
    )
    # Add total and share columns
    pivot["total_beverage_revenue"] = pivot.sum(axis=1)
    for col in BEVERAGE_DIVISIONS.values():
        if col in pivot.columns:
            pivot[f"{col}_share_pct"] = (
                pivot[col] / pivot["total_beverage_revenue"] * 100
            ).round(1)
    return pivot


def branch_top_items(bev_df: pd.DataFrame, n: int = 5) -> Dict[str, pd.DataFrame]:
    """Top N items by revenue per branch."""
    result = {}
    for branch, grp in bev_df.groupby("branch"):
        top = (
            grp.groupby("item")
            .agg(revenue=("revenue", "sum"), qty=("qty", "sum"))
            .sort_values("revenue", ascending=False)
            .head(n)
            .reset_index()
        )
        top["rev_per_unit"] = (top["revenue"] / top["qty"].replace(0, np.nan)).round(0)
        result[branch] = top
    return result


# ─────────────────────────────────────────────────────────
# Growth Opportunity Matrix
# ─────────────────────────────────────────────────────────

def growth_opportunity_matrix(bev_df: pd.DataFrame) -> pd.DataFrame:
    """
    Identify items that are:
      - HIGH revenue per unit (premium positioning opportunity)
      - LOW current volume (under-penetrated, room to grow)
    Quadrant classification:
      - Stars: high vol + high rev/unit (defend & grow)
      - Cash Cows: high vol + low rev/unit (protect margin)
      - Opportunities: low vol + high rev/unit (promote hard!)
      - Dogs: low vol + low rev/unit (consider removing)
    """
    agg = (
        bev_df.groupby(["item", "category"])
        .agg(total_revenue=("revenue", "sum"), total_qty=("qty", "sum"))
        .reset_index()
    )
    agg = agg[agg["total_qty"] > 0]
    agg["rev_per_unit"] = agg["total_revenue"] / agg["total_qty"]

    qty_median = agg["total_qty"].median()
    rev_median = agg["rev_per_unit"].median()

    def classify(row):
        high_vol = row["total_qty"] >= qty_median
        high_rev = row["rev_per_unit"] >= rev_median
        if high_vol and high_rev:
            return "STAR"
        elif high_vol and not high_rev:
            return "CASH COW"
        elif not high_vol and high_rev:
            return "OPPORTUNITY"
        else:
            return "DOG"

    agg["quadrant"] = agg.apply(classify, axis=1)
    agg["rev_per_unit"] = agg["rev_per_unit"].round(0)
    return agg.sort_values(["quadrant", "total_revenue"], ascending=[True, False])


# ─────────────────────────────────────────────────────────
# Strategy Recommendations
# ─────────────────────────────────────────────────────────

def generate_strategy(
    bev_df: pd.DataFrame,
    pareto_by_cat: Dict[str, pd.DataFrame],
    opp_matrix: pd.DataFrame,
) -> List[Dict]:
    """
    Generate actionable strategy recommendations.
    """
    recommendations = []

    # 1. Promote OPPORTUNITY quadrant items (high value, low volume)
    opps = opp_matrix[opp_matrix["quadrant"] == "OPPORTUNITY"].head(8)
    if not opps.empty:
        recommendations.append({
            "type": "PROMOTION",
            "priority": "HIGH",
            "title": "Feature Under-Penetrated High-Value Beverages",
            "items": opps["item"].tolist(),
            "rationale": (
                f"These {len(opps)} items command above-median revenue per unit "
                "but are selling below the network median volume — strong promotion "
                "or combo bundling can unlock significant upside."
            ),
            "action": "Place on menu board + social media spotlight; create limited-time combo with top food item.",
        })

    # 2. Defend STARS
    stars = opp_matrix[opp_matrix["quadrant"] == "STAR"].head(5)
    if not stars.empty:
        recommendations.append({
            "type": "DEFEND",
            "priority": "HIGH",
            "title": "Protect Star Products",
            "items": stars["item"].tolist(),
            "rationale": "High volume AND high revenue per unit — these are the core revenue drivers.",
            "action": "Ensure consistent availability, quality control, and staff training focus on these items.",
        })

    # 3. Coffee-specific: Frappe vs Hot Coffee
    coffee_pareto = pareto_by_cat.get("coffee", pd.DataFrame())
    frappe_pareto = pareto_by_cat.get("frappe", pd.DataFrame())
    shake_pareto = pareto_by_cat.get("milkshake", pd.DataFrame())

    if not coffee_pareto.empty and not frappe_pareto.empty:
        total_coffee = coffee_pareto["total_revenue"].sum()
        total_frappe = frappe_pareto["total_revenue"].sum()
        if total_frappe > total_coffee:
            recommendations.append({
                "type": "PRICING",
                "priority": "MEDIUM",
                "title": "Frappes Outperform Hot Coffee — Price Alignment Opportunity",
                "rationale": (
                    f"Frappes generate {total_frappe/total_coffee:.1f}x the revenue of hot coffee. "
                    "This signals strong cold beverage preference. Raise frappe prices by 5-8% "
                    "and create hot-coffee loyalty offer to develop that segment."
                ),
                "action": "A/B test +5% price on top 3 frappes. Add loyalty stamp card for hot coffee.",
            })
        else:
            recommendations.append({
                "type": "GROWTH",
                "priority": "MEDIUM",
                "title": "Hot Coffee Dominates — Expand Seasonal Variants",
                "rationale": (
                    f"Hot coffee generates {total_coffee/max(total_frappe,1):.1f}x frappe revenue. "
                    "Introduce seasonal specials (Pumpkin Spice, Hazelnut Limited) to attract new segments."
                ),
                "action": "Launch 2-3 seasonal hot coffee SKUs per quarter.",
            })

    # 4. Milkshake push
    if not shake_pareto.empty:
        top_shake = shake_pareto.iloc[0]["item"] if not shake_pareto.empty else "N/A"
        recommendations.append({
            "type": "BUNDLE",
            "priority": "MEDIUM",
            "title": f"Milkshake Upsell Bundle — anchor: {top_shake}",
            "items": shake_pareto.head(3)["item"].tolist() if not shake_pareto.empty else [],
            "rationale": (
                "Milkshakes have the highest revenue-per-unit in the cold beverage category. "
                "Bundle top milkshakes with chimney cake items to drive avg. basket value."
            ),
            "action": "Introduce 'Shake + Dessert' combo at 8-10% discount vs. separate price.",
        })

    # 5. Dogs — consider removing
    dogs = opp_matrix[opp_matrix["quadrant"] == "DOG"]
    if len(dogs) > 3:
        recommendations.append({
            "type": "MENU PRUNING",
            "priority": "LOW",
            "title": f"Review {len(dogs)} Under-Performing Items",
            "items": dogs.head(5)["item"].tolist(),
            "rationale": "Low volume AND low revenue per unit. Menu complexity hurts operational speed.",
            "action": "Remove or replace bottom 20% of DOG items. Simplify menu board.",
        })

    return recommendations


# ─────────────────────────────────────────────────────────
# Master Runner
# ─────────────────────────────────────────────────────────

def run_coffee_milkshake_analysis() -> Dict:
    """Full coffee & milkshake growth strategy pipeline."""
    bev_df = load_beverage_data()

    if bev_df.empty:
        return {"error": "No beverage data loaded"}

    # Pareto per category
    pareto_by_cat = {}
    for div, cat in BEVERAGE_DIVISIONS.items():
        pareto_by_cat[cat] = pareto_analysis(bev_df, category=cat)

    # Cross-branch
    branch_rev = cross_branch_category_revenue(bev_df)
    branch_tops = branch_top_items(bev_df, n=5)

    # Opportunity matrix
    opp_matrix = growth_opportunity_matrix(bev_df)

    # Recommendations
    strategy = generate_strategy(bev_df, pareto_by_cat, opp_matrix)

    # Summary stats
    total_bev_rev = bev_df["revenue"].sum()
    cat_totals = bev_df.groupby("category")["revenue"].sum().sort_values(ascending=False)

    return {
        "beverage_data": bev_df,
        "pareto_by_cat": pareto_by_cat,
        "branch_category_revenue": branch_rev,
        "branch_top_items": branch_tops,
        "opportunity_matrix": opp_matrix,
        "strategy_recommendations": strategy,
        "total_beverage_revenue": total_bev_rev,
        "category_totals": cat_totals,
    }


def print_coffee_milkshake_report(result: Dict) -> None:
    if "error" in result:
        print(f"Error: {result['error']}")
        return

    print("\n" + "=" * 65)
    print("  CONUT — COFFEE & MILKSHAKE GROWTH STRATEGY REPORT")
    print("=" * 65)

    cat_totals = result["category_totals"]
    total = result["total_beverage_revenue"]
    print(f"\n[1] BEVERAGE REVENUE BY CATEGORY  (Total: {total:,.0f})")
    for cat, rev in cat_totals.items():
        share = rev / total * 100
        bar = "#" * int(share / 2)
        print(f"  {cat:<20}: {rev:>20,.0f}  ({share:>5.1f}%)  {bar}")

    print("\n[2] TOP ITEMS PER CATEGORY (Pareto Top-10%)")
    for cat, pareto in result["pareto_by_cat"].items():
        if pareto.empty:
            continue
        stars = pareto[pareto["is_top_20pct"]]
        print(f"\n  -- {cat.upper()} ({len(stars)} items drive 80% of revenue) --")
        for _, r in stars.head(5).iterrows():
            print(f"    {r['item']:<40} Rev: {r['total_revenue']:>15,.0f}  "
                  f"({r['rev_share_pct']:.1f}%)  "
                  f"Rev/unit: {r['revenue_per_unit']:>10,.0f}")

    print("\n[3] GROWTH OPPORTUNITY MATRIX")
    opp = result["opportunity_matrix"]
    for quad in ["STAR", "OPPORTUNITY", "CASH COW", "DOG"]:
        items = opp[opp["quadrant"] == quad]
        emoji = {"STAR": "★", "OPPORTUNITY": "!", "CASH COW": "$", "DOG": "x"}.get(quad, "")
        print(f"\n  {emoji} {quad} ({len(items)} items)")
        for _, r in items.head(5).iterrows():
            print(f"    [{r['category']:<12}] {r['item']:<40} "
                  f"Qty: {r['total_qty']:>6.0f}  Rev/unit: {r['rev_per_unit']:>10,.0f}")

    print("\n[4] STRATEGIC RECOMMENDATIONS")
    for i, rec in enumerate(result["strategy_recommendations"], 1):
        print(f"\n  [{i}] [{rec['priority']}] {rec['title']}")
        print(f"       Type    : {rec['type']}")
        print(f"       Why     : {rec['rationale']}")
        print(f"       Action  : {rec['action']}")
        if rec.get("items"):
            print(f"       Items   : {', '.join(rec['items'][:5])}")

    print("\n" + "=" * 65)


if __name__ == "__main__":
    result = run_coffee_milkshake_analysis()
    print_coffee_milkshake_report(result)
