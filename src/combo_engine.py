"""
combo_engine.py
===============
Combo Optimization for Conut — Market Basket Analysis on Delivery Orders.

Methodology
-----------
REP_S_00502.csv contains per-customer delivery orders with individual line items.
We treat each customer's order as a "basket" and run:

1. Basket construction — group items per customer per branch (exclude modifiers,
   delivery charges, and zero-revenue add-ons; keep meaningful SKUs only).
2. Frequent itemset mining — Apriori algorithm (custom implementation; no mlxtend
   dependency required) to find item combinations that co-occur above min_support.
3. Association rule generation — compute support, confidence, and lift for each
   rule. Lift > 1 = items are bought together more often than by chance.
4. Combo recommendations — top rules ranked by lift × confidence for pricing.
5. Revenue uplift estimate — if all single-item buyers of A were upsold B,
   estimated incremental revenue added.

Output
------
  - combos_df      : DataFrame of top association rules (antecedent → consequent)
  - basket_summary : per-branch basket stats
  - recommendations: ranked combo deals with estimated uplift
"""
from __future__ import annotations

import re
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.data_loader import _read_csv_rows, _clean_number, KNOWN_BRANCHES

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "REP_S_00502.csv"

# ─────────────────────────────────────────────────────────
# Items to EXCLUDE from basket analysis
# (modifiers, free add-ons, logistics, customisations)
# ─────────────────────────────────────────────────────────
EXCLUDE_PATTERNS = [
    r"DELIVERY CHARGE", r"PRESSED", r"REGULAR\.", r"^NO ", r"\(R\)$",
    r"WHIPPED CREAM", r"SPREAD", r"SAUCE", r"TOPPING", r"DIP",
    r"CINNAMON", r"ICE CREAM ON", r"SWITCH TO", r"SEND CUTLERY",
    r"DONT SEND", r"TAKE AWAY", r"FULL FAT MILK$", r"WATER$",
    r"PISTACHIO TOPPING", r"NO TOPPINGS", r"ADD ICE CREAM",
]

_EXCLUDE_RE = re.compile("|".join(EXCLUDE_PATTERNS), re.IGNORECASE)


def _is_modifier(item: str) -> bool:
    """Return True if this item is a modifier/add-on, not a sellable SKU."""
    return bool(_EXCLUDE_RE.search(item))


def _normalise_item(item: str) -> str:
    """Strip leading spaces, bracket prefixes, and trailing punctuation."""
    s = item.strip().lstrip("[").rstrip("].,")
    return s


# ─────────────────────────────────────────────────────────
# Basket Builder
# ─────────────────────────────────────────────────────────

def build_baskets() -> Tuple[pd.DataFrame, Dict[str, List[List[str]]]]:
    """
    Parse REP_S_00502.csv and return:
      - transactions_df: customer | branch | items (list) | total_spend | n_items
      - baskets_by_branch: {branch: [[item, ...], ...]}
    """
    rows = _read_csv_rows(DATA_FILE)

    branch = None
    customer = None
    current_items: List[str] = []
    current_total = 0.0
    transactions = []

    for row in rows:
        if not row:
            continue
        first = row[0].strip()

        # Detect branch line: "Branch :Conut - Tyre" or "Branch: Conut"
        m = re.match(r"Branch\s*:\s*(.+)", first, re.IGNORECASE)
        if m:
            branch = m.group(1).strip()
            continue

        # Detect customer header line: "Person_XXXX" or "0 Person_XXXX"
        if re.match(r"^(0\s+)?Person_\d+", first):
            # Save previous customer's basket if valid
            if customer and current_items and current_total > 0:
                clean_items = [_normalise_item(i) for i in current_items
                               if not _is_modifier(i)]
                clean_items = list(dict.fromkeys(clean_items))  # deduplicate
                if clean_items:
                    transactions.append({
                        "customer": customer,
                        "branch": branch,
                        "items": clean_items,
                        "total_spend": current_total,
                        "n_items": len(clean_items),
                    })
            customer = first.strip()
            current_items = []
            current_total = 0.0
            continue

        # Detect total line: "Total :" with amount in col[3]
        if re.match(r"^Total\s*:", first):
            if len(row) >= 4:
                t = _clean_number(row[3])
                if not np.isnan(t) and t > 0:
                    current_total = t
            continue

        # Skip page headers / noise
        if re.match(r"\d{2}-\w{3}-\d{2}", first):
            continue
        if first in ("Full Name",) or (first == "" and len(row) < 3):
            continue

        # Item line: row[0] is empty, row[1]=qty, row[2]=description, row[3]=price
        if first == "" and len(row) >= 3:
            qty_raw = row[1].strip() if len(row) > 1 else ""
            desc = row[2].strip() if len(row) > 2 else ""
            try:
                qty = int(qty_raw)
            except Exception:
                qty = 0
            if qty > 0 and desc:
                current_items.append(desc)

    # Flush last customer
    if customer and current_items and current_total > 0:
        clean_items = [_normalise_item(i) for i in current_items
                       if not _is_modifier(i)]
        clean_items = list(dict.fromkeys(clean_items))
        if clean_items:
            transactions.append({
                "customer": customer,
                "branch": branch,
                "items": clean_items,
                "total_spend": current_total,
                "n_items": len(clean_items),
            })

    df = pd.DataFrame(transactions)

    # Build per-branch basket lists
    baskets_by_branch: Dict[str, List[List[str]]] = defaultdict(list)
    for _, row_t in df.iterrows():
        if row_t["branch"]:
            baskets_by_branch[row_t["branch"]].append(row_t["items"])

    return df, dict(baskets_by_branch)


# ─────────────────────────────────────────────────────────
# Apriori (Custom — no external dependency)
# ─────────────────────────────────────────────────────────

def _get_item_support(baskets: List[List[str]], min_support: float) -> Dict[frozenset, float]:
    """Calculate support for all individual items and filter by min_support."""
    n = len(baskets)
    counts: Dict[frozenset, int] = defaultdict(int)
    for basket in baskets:
        for item in set(basket):
            counts[frozenset([item])] += 1
    return {k: v / n for k, v in counts.items() if v / n >= min_support}


def _get_pair_support(baskets: List[List[str]], items: List[str],
                      min_support: float) -> Dict[frozenset, float]:
    """Calculate support for all pairs among frequent items."""
    n = len(baskets)
    counts: Dict[frozenset, int] = defaultdict(int)
    for basket in baskets:
        basket_set = set(basket)
        # Only consider items already passing min_support
        present = [i for i in items if i in basket_set]
        for a, b in combinations(present, 2):
            counts[frozenset([a, b])] += 1
    return {k: v / n for k, v in counts.items() if v / n >= min_support}


def run_apriori(
    baskets: List[List[str]],
    min_support: float = 0.03,
    min_confidence: float = 0.20,
    min_lift: float = 1.5,
) -> pd.DataFrame:
    """
    Run Apriori on a list of baskets and return association rules.
    """
    if not baskets:
        return pd.DataFrame()

    n = len(baskets)

    # L1: frequent items
    item_support = _get_item_support(baskets, min_support)
    freq_items = [list(k)[0] for k in item_support]

    # L2: frequent pairs
    pair_support = _get_pair_support(baskets, freq_items, min_support)

    rules = []
    for pair, supp in pair_support.items():
        items = list(pair)
        for antecedent, consequent in [(items[0], items[1]), (items[1], items[0])]:
            ant_supp = item_support.get(frozenset([antecedent]), 0)
            con_supp = item_support.get(frozenset([consequent]), 0)
            if ant_supp == 0 or con_supp == 0:
                continue
            confidence = supp / ant_supp
            lift = confidence / con_supp
            if confidence >= min_confidence and lift >= min_lift:
                rules.append({
                    "antecedent": antecedent,
                    "consequent": consequent,
                    "support": round(supp, 4),
                    "confidence": round(confidence, 4),
                    "lift": round(lift, 4),
                    "n_transactions": int(supp * n),
                })

    if not rules:
        return pd.DataFrame()

    df = pd.DataFrame(rules).sort_values(
        ["lift", "confidence"], ascending=False
    ).drop_duplicates(subset=["antecedent", "consequent"]).reset_index(drop=True)
    return df


# ─────────────────────────────────────────────────────────
# Revenue Uplift Estimator
# ─────────────────────────────────────────────────────────

def estimate_combo_uplift(
    rules: pd.DataFrame,
    transactions_df: pd.DataFrame,
    top_n: int = 5,
) -> pd.DataFrame:
    """
    For the top N rules, estimate revenue uplift if combo is promoted.
    Uplift logic: customers who bought antecedent without consequent
    × average order value of consequent.
    """
    if rules.empty or transactions_df.empty:
        return pd.DataFrame()

    results = []
    avg_order = transactions_df["total_spend"].mean()

    for _, rule in rules.head(top_n).iterrows():
        ant = rule["antecedent"]
        con = rule["consequent"]

        buyers_ant = transactions_df[
            transactions_df["items"].apply(lambda x: ant in x)
        ]
        buyers_both = buyers_ant[
            buyers_ant["items"].apply(lambda x: con in x)
        ]
        buyers_ant_only = len(buyers_ant) - len(buyers_both)

        # If we convert (confidence% of) ant-only buyers to buy the combo
        conversion_gain = buyers_ant_only * (1 - rule["confidence"])
        estimated_uplift = conversion_gain * avg_order * 0.15  # 15% margin increase assumption

        results.append({
            "combo": f"{ant}  +  {con}",
            "antecedent": ant,
            "consequent": con,
            "lift": rule["lift"],
            "confidence": rule["confidence"],
            "support": rule["support"],
            "n_paired_transactions": len(buyers_both),
            "uncaptured_buyers": buyers_ant_only,
            "estimated_revenue_uplift": round(estimated_uplift, 0),
        })

    return pd.DataFrame(results)


# ─────────────────────────────────────────────────────────
# Basket Summary
# ─────────────────────────────────────────────────────────

def basket_summary(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Per-branch basket statistics."""
    if transactions_df.empty:
        return pd.DataFrame()

    rows = []
    for branch, grp in transactions_df.groupby("branch"):
        rows.append({
            "branch": branch,
            "n_customers": len(grp),
            "avg_basket_size": grp["n_items"].mean().round(2),
            "avg_spend_per_order": grp["total_spend"].mean().round(0),
            "total_revenue": grp["total_spend"].sum().round(0),
            "pct_multi_item_orders": (grp["n_items"] > 1).mean().round(3) * 100,
            "top_item": (
                pd.Series([i for items in grp["items"] for i in items])
                .value_counts().index[0]
                if not grp.empty else "N/A"
            ),
        })
    return pd.DataFrame(rows).set_index("branch")


# ─────────────────────────────────────────────────────────
# Master Runner
# ─────────────────────────────────────────────────────────

def run_combo_analysis(
    min_support: float = 0.03,
    min_confidence: float = 0.15,
    min_lift: float = 1.3,
) -> Dict:
    """
    Full combo analysis pipeline.
    Returns dict with keys:
      transactions, baskets_by_branch, rules_by_branch,
      top_rules, basket_stats, uplift_estimates
    """
    transactions_df, baskets_by_branch = build_baskets()

    # Run Apriori per branch and globally
    rules_by_branch = {}
    for branch, baskets in baskets_by_branch.items():
        rules = run_apriori(baskets, min_support, min_confidence, min_lift)
        rules_by_branch[branch] = rules

    # Global rules (all branches combined)
    all_baskets = [b for blist in baskets_by_branch.values() for b in blist]
    global_rules = run_apriori(all_baskets, min_support, min_confidence, min_lift)

    stats = basket_summary(transactions_df)
    uplift = estimate_combo_uplift(global_rules, transactions_df, top_n=10)

    return {
        "transactions": transactions_df,
        "baskets_by_branch": baskets_by_branch,
        "rules_by_branch": rules_by_branch,
        "global_rules": global_rules,
        "basket_stats": stats,
        "uplift_estimates": uplift,
    }


def print_combo_report(result: Dict) -> None:
    print("\n" + "=" * 65)
    print("  CONUT — COMBO OPTIMIZATION REPORT")
    print("=" * 65)

    stats = result["basket_stats"]
    if not stats.empty:
        print("\n[1] BASKET STATISTICS BY BRANCH")
        print(stats[["n_customers", "avg_basket_size", "avg_spend_per_order",
                      "pct_multi_item_orders", "top_item"]].to_string())

    global_rules = result["global_rules"]
    if not global_rules.empty:
        print(f"\n[2] TOP ASSOCIATION RULES (network-wide, {len(global_rules)} rules found)")
        print(f"{'Antecedent':<35} {'Consequent':<35} {'Supp':>6} {'Conf':>6} {'Lift':>6}")
        print("-" * 90)
        for _, r in global_rules.head(15).iterrows():
            print(f"{r['antecedent']:<35} {r['consequent']:<35} "
                  f"{r['support']:>6.3f} {r['confidence']:>6.3f} {r['lift']:>6.2f}")

    uplift = result["uplift_estimates"]
    if not uplift.empty:
        print(f"\n[3] TOP COMBO DEALS — ESTIMATED REVENUE UPLIFT")
        print(f"{'Combo':<65} {'Lift':>6} {'Est. Uplift':>14}")
        print("-" * 90)
        for _, r in uplift.iterrows():
            print(f"{r['combo']:<65} {r['lift']:>6.2f} {r['estimated_revenue_uplift']:>14,.0f}")

    # Per-branch top rules
    print("\n[4] TOP RULES PER BRANCH")
    for branch, rules in result["rules_by_branch"].items():
        if rules.empty:
            print(f"\n  {branch}: no rules above threshold")
        else:
            print(f"\n  {branch}  ({len(rules)} rules)")
            top = rules.head(5)
            for _, r in top.iterrows():
                print(f"    {r['antecedent']} + {r['consequent']}  "
                      f"(lift={r['lift']:.2f}, conf={r['confidence']:.2f})")

    print("\n" + "=" * 65)


if __name__ == "__main__":
    result = run_combo_analysis()
    print_combo_report(result)
