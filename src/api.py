"""
api.py
======
FastAPI application exposing all 5 Conut AI Chief of Operations objectives.
Designed for OpenClaw integration — each endpoint accepts natural-language
query parameters and returns structured JSON responses.

Endpoints
---------
GET  /health                   — liveness probe
GET  /expansion                — expansion feasibility analysis
GET  /staffing/{branch}        — staffing recommendation for a branch
GET  /combos                   — combo optimization (top association rules)
GET  /forecast/{branch}        — demand forecast for a branch (Jan-Mar 2026)
GET  /coffee-strategy          — coffee & milkshake growth strategy
GET  /ask                      — natural language query dispatcher (OpenClaw hook)

OpenClaw Integration
--------------------
OpenClaw can call /ask with a free-text `query` parameter and the system
will route to the appropriate engine and return structured JSON.

Example OpenClaw queries:
  GET /ask?query=should we open a new branch
  GET /ask?query=how many staff do we need at Conut Jnah evening shift
  GET /ask?query=what combos should we promote
  GET /ask?query=forecast demand for Main Street Coffee
  GET /ask?query=how do we grow milkshake sales
"""
from __future__ import annotations

import re
import traceback
from functools import lru_cache
from typing import Any, Dict, Optional

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.responses import JSONResponse
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.expansion_engine import run_expansion_analysis
from src.staffing_engine import run_staffing_analysis
from src.combo_engine import run_combo_analysis
from src.demand_forecast_engine import run_demand_forecast
from src.coffee_milkshake_engine import run_coffee_milkshake_analysis

# ─────────────────────────────────────────────────────────
# Cache layer — analyses are expensive; cache for the session
# ─────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _cached_expansion():
    return run_expansion_analysis()

@lru_cache(maxsize=1)
def _cached_staffing():
    return run_staffing_analysis()

@lru_cache(maxsize=1)
def _cached_combos():
    return run_combo_analysis()

@lru_cache(maxsize=1)
def _cached_forecast():
    return run_demand_forecast()

@lru_cache(maxsize=1)
def _cached_coffee():
    return run_coffee_milkshake_analysis()


# ─────────────────────────────────────────────────────────
# Response serializers — convert DataFrames to dicts
# ─────────────────────────────────────────────────────────

def _safe_dict(obj) -> Any:
    """Recursively convert pandas/numpy objects to JSON-serialisable types."""
    import numpy as np
    import pandas as pd
    if isinstance(obj, pd.DataFrame):
        return obj.reset_index().to_dict(orient="records")
    if isinstance(obj, pd.Series):
        return obj.reset_index().to_dict(orient="records")
    if isinstance(obj, dict):
        return {k: _safe_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_safe_dict(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


# ─────────────────────────────────────────────────────────
# Natural Language Router (OpenClaw /ask hook)
# ─────────────────────────────────────────────────────────

INTENT_PATTERNS = {
    "expansion": [
        r"expand", r"new branch", r"open.*branch", r"feasib",
        r"replicate", r"5th branch", r"location",
    ],
    "staffing": [
        r"staff", r"employee", r"shift", r"schedule", r"headcount",
        r"workers?", r"how many people",
    ],
    "combos": [
        r"combo", r"bundle", r"pair", r"together", r"association",
        r"market basket", r"frequently bought",
    ],
    "forecast": [
        r"forecast", r"predict", r"demand", r"next month", r"future",
        r"expect", r"projection", r"2026",
    ],
    "coffee": [
        r"coffee", r"milkshake", r"beverage", r"drinks?", r"frappe",
        r"grow.*sales", r"strategy", r"shake",
    ],
}

KNOWN_BRANCHES = ["Conut - Tyre", "Conut Jnah", "Main Street Coffee", "Conut"]


def detect_intent(query: str) -> tuple[str, Optional[str]]:
    """Return (intent, branch_if_mentioned)."""
    q = query.lower()
    scores = {}
    for intent, patterns in INTENT_PATTERNS.items():
        scores[intent] = sum(1 for p in patterns if re.search(p, q, re.IGNORECASE))
    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        best = "unknown"

    # Extract branch name if mentioned
    branch = None
    for b in KNOWN_BRANCHES:
        if b.lower() in q:
            branch = b
            break

    return best, branch


# ─────────────────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────────────────

if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="Conut AI Chief of Operations",
        description=(
            "AI-driven operations intelligence for Conut's 4-branch sweets & beverages network. "
            "Covers: Expansion Feasibility, Shift Staffing, Combo Optimization, "
            "Demand Forecasting, and Coffee & Milkshake Growth Strategy. "
            "Integrated with OpenClaw via the /ask natural language endpoint."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    @app.get("/health")
    def health():
        """Liveness probe for OpenClaw."""
        return {"status": "ok", "service": "conut-ai-ops", "version": "1.0.0"}

    # ── 1. Expansion ──────────────────────────────────────────
    @app.get("/expansion")
    def expansion():
        """
        Expansion feasibility analysis.
        Returns branch scores, GO/CAUTION/NO-GO decision, and new branch profile.
        """
        try:
            rec = _cached_expansion()
            payload = {
                "decision": rec["decision"],
                "confidence": rec["confidence"],
                "best_template_branch": rec["best_template_branch"],
                "justifications": rec["justifications"],
                "risks": rec["risks"],
                "branch_scores": _safe_dict(rec["branch_scores"]),
                "new_branch_profile": _safe_dict(rec["new_branch_profile"]),
            }
            return JSONResponse(content=payload)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ── 2. Staffing ───────────────────────────────────────────
    @app.get("/staffing/{branch}")
    def staffing(branch: str):
        """
        Staffing recommendation for a specific branch.
        Branch values: 'Conut', 'Conut - Tyre', 'Conut Jnah', 'Main Street Coffee'
        """
        try:
            result = _cached_staffing()
            rec = result["staffing_recommendations"]
            att_stats = result["attendance_stats"]
            prod = result["productivity_index"]

            # Fuzzy branch match — prefer exact, then longest common substring
            branch_lower = branch.lower()
            candidates = []
            for b in rec.keys():
                b_lower = b.lower()
                if b_lower == branch_lower:
                    candidates.append((0, b))   # exact match — highest priority
                elif branch_lower in b_lower:
                    candidates.append((1, b))   # query is substring of key
                elif b_lower in branch_lower:
                    candidates.append((2, b))   # key is substring of query
            # Sort: exact first, then by descending key length (longest = most specific)
            candidates.sort(key=lambda x: (x[0], -len(x[1])))
            matched = candidates[0][1] if candidates else None
            if not matched:
                raise HTTPException(
                    status_code=404,
                    detail=f"Branch '{branch}' not found. Available: {list(rec.keys())}"
                )

            payload = {
                "branch": matched,
                "staffing_by_shift": rec.get(matched, {}),
                "attendance_summary": _safe_dict(
                    att_stats.loc[[matched]] if matched in att_stats.index else {}
                ),
                "productivity": _safe_dict(
                    prod.loc[[matched]] if matched in prod.index else {}
                ),
                "anomalies_count": len(result["anomalies"][
                    result["anomalies"]["branch"] == matched
                ]) if not result["anomalies"].empty else 0,
            }
            return JSONResponse(content=_safe_dict(payload))
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ── 3. Combos ─────────────────────────────────────────────
    @app.get("/combos")
    def combos(
        branch: Optional[str] = Query(None, description="Filter by branch name"),
        top_n: int = Query(10, description="Number of top rules to return"),
    ):
        """
        Market basket analysis — top combo recommendations with lift scores.
        """
        try:
            result = _cached_combos()
            if branch:
                branch_lower = branch.lower()
                candidates = []
                for b in result["rules_by_branch"].keys():
                    b_lower = b.lower()
                    if b_lower == branch_lower:
                        candidates.append((0, b))
                    elif branch_lower in b_lower:
                        candidates.append((1, b))
                    elif b_lower in branch_lower:
                        candidates.append((2, b))
                candidates.sort(key=lambda x: (x[0], -len(x[1])))
                matched = candidates[0][1] if candidates else None
                rules = result["rules_by_branch"].get(matched, result["global_rules"])
            else:
                rules = result["global_rules"]

            payload = {
                "source": branch or "all branches",
                "n_rules_found": len(rules),
                "top_rules": _safe_dict(rules.head(top_n)),
                "basket_stats": _safe_dict(result["basket_stats"]),
                "uplift_estimates": _safe_dict(result["uplift_estimates"].head(top_n)),
            }
            return JSONResponse(content=payload)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ── 4. Forecast ───────────────────────────────────────────
    @app.get("/forecast/{branch}")
    def forecast(branch: str):
        """
        3-month demand forecast for a branch (Jan-Mar 2026).
        Includes ensemble forecast + 80% and 95% prediction intervals.
        """
        try:
            result = _cached_forecast()
            forecasts = result["forecasts"]

            branch_lower = branch.lower()
            candidates = []
            for b in forecasts.keys():
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
                    detail=f"Branch '{branch}' not found. Available: {list(forecasts.keys())}"
                )

            payload = {
                "branch": matched,
                "forecast": forecasts[matched],
                "network_context": {
                    "forecast_months": result["forecast_months"],
                    "network_3m_forecast": result["network_forecast_3m"],
                },
            }
            return JSONResponse(content=_safe_dict(payload))
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ── 5. Coffee & Milkshake ─────────────────────────────────
    @app.get("/coffee-strategy")
    def coffee_strategy():
        """
        Coffee & milkshake growth strategy with Pareto analysis,
        opportunity matrix, and actionable recommendations.
        """
        try:
            result = _cached_coffee()
            if "error" in result:
                raise HTTPException(status_code=500, detail=result["error"])

            pareto_summary = {}
            for cat, df in result["pareto_by_cat"].items():
                if not df.empty:
                    stars = df[df["is_top_20pct"]]
                    pareto_summary[cat] = {
                        "items_driving_80pct_revenue": len(stars),
                        "top_3": stars.head(3)[["item", "total_revenue",
                                                 "rev_share_pct"]].to_dict(orient="records"),
                    }

            payload = {
                "total_beverage_revenue": float(result["total_beverage_revenue"]),
                "category_breakdown": _safe_dict(result["category_totals"]),
                "pareto_by_category": pareto_summary,
                "opportunity_matrix_summary": {
                    q: len(result["opportunity_matrix"][
                        result["opportunity_matrix"]["quadrant"] == q
                    ])
                    for q in ["STAR", "OPPORTUNITY", "CASH COW", "DOG"]
                },
                "top_opportunities": _safe_dict(
                    result["opportunity_matrix"][
                        result["opportunity_matrix"]["quadrant"] == "OPPORTUNITY"
                    ].head(8)[["item", "category", "total_qty", "rev_per_unit"]]
                ),
                "strategy_recommendations": result["strategy_recommendations"],
                "strategies_count": len(result["strategy_recommendations"]),
            }
            return JSONResponse(content=_safe_dict(payload))
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ── 6. Natural Language /ask (OpenClaw main hook) ─────────
    @app.get("/ask")
    def ask(
        query: str = Query(..., description="Natural language operational query"),
    ):
        """
        Natural language query dispatcher for OpenClaw.
        Routes queries to the appropriate engine based on detected intent.

        Examples:
        - 'Should we open a new branch?'
        - 'How many staff do we need at Conut Jnah evening shift?'
        - 'What combos should we promote to delivery customers?'
        - 'Forecast demand for Main Street Coffee in Q1 2026'
        - 'How do we grow milkshake and coffee sales?'
        """
        intent, branch = detect_intent(query)

        try:
            if intent == "expansion":
                rec = _cached_expansion()
                return JSONResponse(content=_safe_dict({
                    "query": query, "intent": "expansion",
                    "decision": rec["decision"],
                    "confidence": rec["confidence"],
                    "best_template_branch": rec["best_template_branch"],
                    "justifications": rec["justifications"],
                    "risks": rec["risks"],
                    "branch_scores": rec["branch_scores"]["expansion_score"].to_dict(),
                }))
            elif intent == "staffing":
                b = branch or "Conut Jnah"
                result = staffing(b)
                # inject intent into the response
                body = result.body if hasattr(result, "body") else None
                if body:
                    import json as _json
                    data = _json.loads(body)
                    data["intent"] = "staffing"
                    data["query"] = query
                    return JSONResponse(content=data)
                return result
            elif intent == "combos":
                result = combos(branch=branch, top_n=10)
                body = result.body if hasattr(result, "body") else None
                if body:
                    import json as _json
                    data = _json.loads(body)
                    data["intent"] = "combos"
                    data["query"] = query
                    return JSONResponse(content=data)
                return result
            elif intent == "forecast":
                b = branch or "all"
                if b == "all":
                    result = _cached_forecast()
                    return JSONResponse(content={
                        "query": query, "intent": "forecast",
                        "all_forecasts": _safe_dict({
                            br: {
                                k: v for k, v in fc.items()
                                if k in ("trajectory", "forecast_ensemble",
                                         "forecast_months", "inventory_signal",
                                         "monthly_growth_rate_hist")
                            }
                            for br, fc in result["forecasts"].items()
                            if "error" not in fc
                        }),
                    })
                result = forecast(b)
                body = result.body if hasattr(result, "body") else None
                if body:
                    import json as _json
                    data = _json.loads(body)
                    data["intent"] = "forecast"
                    data["query"] = query
                    return JSONResponse(content=data)
                return result
            elif intent == "coffee":
                result = coffee_strategy()
                body = result.body if hasattr(result, "body") else None
                if body:
                    import json as _json
                    data = _json.loads(body)
                    data["intent"] = "coffee"
                    data["query"] = query
                    return JSONResponse(content=data)
                return result
            else:
                return JSONResponse(content={
                    "query": query,
                    "intent": "unknown",
                    "message": (
                        "Query not understood. Try asking about: "
                        "expansion, staffing, combos, demand forecast, "
                        "or coffee/milkshake strategy."
                    ),
                    "available_endpoints": [
                        "/expansion", "/staffing/{branch}",
                        "/combos", "/forecast/{branch}",
                        "/coffee-strategy",
                    ],
                })
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing query: {e}")


# ─────────────────────────────────────────────────────────
# Standalone runner
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not FASTAPI_AVAILABLE:
        print("FastAPI not installed. Run: pip install fastapi uvicorn")
        print("Falling back to CLI mode — printing all reports:")
        print("\n--- EXPANSION ---")
        from src.expansion_engine import print_report
        print_report(run_expansion_analysis())

        print("\n--- DEMAND FORECAST ---")
        from src.demand_forecast_engine import print_forecast_report
        print_forecast_report(run_demand_forecast())

        print("\n--- COMBOS ---")
        from src.combo_engine import print_combo_report
        print_combo_report(run_combo_analysis())

        print("\n--- COFFEE & MILKSHAKE ---")
        from src.coffee_milkshake_engine import print_coffee_milkshake_report
        print_coffee_milkshake_report(run_coffee_milkshake_analysis())

        print("\n--- STAFFING ---")
        from src.staffing_engine import print_staffing_report
        print_staffing_report(run_staffing_analysis())
    else:
        import uvicorn
        uvicorn.run(
            "src.api:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info",
        )
