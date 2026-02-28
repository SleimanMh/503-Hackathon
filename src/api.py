"""
api.py
======
FastAPI application exposing Conut AI objectives 3 & 4:
  - Objective 3: Branch Expansion Feasibility
  - Objective 4: Shift Staffing Estimation

Designed for OpenClaw integration — each endpoint accepts natural-language
query parameters and returns structured JSON responses.

Endpoints
---------
GET  /health                   — liveness probe
GET  /expansion                — expansion feasibility analysis (Obj 3)
GET  /staffing/{branch}        — staffing recommendation for a branch (Obj 4)
GET  /ask                      — natural language query dispatcher (OpenClaw hook)

OpenClaw Integration
--------------------
OpenClaw can call /ask with a free-text `query` parameter and the system
will route to the appropriate engine and return structured JSON.

Example OpenClaw queries:
  GET /ask?query=should we open a new branch
  GET /ask?query=how many staff do we need at Conut Jnah evening shift
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

from src.objective_3_expansion import run_expansion_analysis
from src.objective_4_staffing import run_staffing_analysis
from src.objective_2_demand_forecast import run_demand_forecast_analysis

# ─────────────────────────────────────────────────────────
# Cache layer — analyses are expensive; cache for the session
# ─────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _cached_expansion():
    return run_expansion_analysis()

@lru_cache(maxsize=1)
def _cached_staffing():
    return run_staffing_analysis()

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
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, float) and (obj != obj):  # NaN
        return None
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
    "forecast": [
        r"forecast", r"demand", r"predict", r"future", r"next month",
        r"inventory", r"trend", r"growth", r"sales projection",
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
            "Covers: Expansion Feasibility (Obj 3) and Shift Staffing Estimation (Obj 4). "
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

    # ── 3. Demand Forecasting ─────────────────────────────────
    @app.get("/forecast/demand")
    def forecast_demand(
        branch: str = Query(..., description="Branch name"),
        months: int = Query(3, ge=1, le=12, description="Forecast horizon in months")
    ):
        """
        Get demand forecast for a specific branch.
        Returns predicted demand with confidence intervals.
        """
        try:
            result = run_demand_forecast_analysis(
                branch=branch,
                months=months,
                analysis_type='forecast'
            )
            return JSONResponse(content=_safe_dict(result))
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/forecast/all-branches")
    def forecast_all_branches(
        months: int = Query(3, ge=1, le=12, description="Forecast horizon in months")
    ):
        """
        Get demand forecasts for all branches.
        Returns comparative analysis across all locations.
        """
        try:
            result = run_demand_forecast_analysis(
                months=months,
                analysis_type='all_branches'
            )
            return JSONResponse(content=_safe_dict(result))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/forecast/trends")
    def forecast_trends(
        branch: str = Query(..., description="Branch name"),
        lookback: int = Query(12, ge=1, le=24, description="Historical months to analyze")
    ):
        """
        Analyze historical trends and seasonality for a branch.
        Returns trend direction, growth rate, and seasonal patterns.
        """
        try:
            result = run_demand_forecast_analysis(
                branch=branch,
                months=lookback,
                analysis_type='trends'
            )
            return JSONResponse(content=_safe_dict(result))
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/forecast/compare")
    def forecast_compare(
        months: int = Query(3, ge=1, le=12, description="Forecast horizon"),
    ):
        """
        Compare forecasted performance across all branches.
        Returns ranking and percentage distribution.
        """
        try:
            all_forecast = run_demand_forecast_analysis(
                months=months,
                analysis_type='all_branches'
            )
            
            # Build comparison list
            comparisons = []
            for branch, fc in all_forecast['branches'].items():
                total_demand = sum(f['predicted_demand'] for f in fc['forecast'])
                growth_rate = fc['model_accuracy'].get('growth_rate', 0) if 'model_accuracy' in fc else 0
                
                comparisons.append({
                    'branch': branch,
                    'total_predicted_demand': total_demand,
                    'percentage_of_total': fc.get('percentage_of_total', 0),
                    'growth_rate': growth_rate
                })
            
            # Sort by demand
            comparisons.sort(key=lambda x: x['total_predicted_demand'], reverse=True)
            
            # Add rank
            for i, comp in enumerate(comparisons, 1):
                comp['rank'] = i
            
            result = {
                'forecast_period': months,
                'comparison': comparisons,
                'recommendation': f"Focus inventory expansion on {comparisons[0]['branch']} (highest forecasted demand)" if comparisons else "No data available"
            }
            
            return JSONResponse(content=_safe_dict(result))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ── 4. Natural Language /ask (OpenClaw main hook) ─────────
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
            elif intent == "forecast":
                b = branch or "Conut Jnah"
                # Extract months if mentioned
                months_match = re.search(r'(\d+)\s*month', query, re.IGNORECASE)
                months = int(months_match.group(1)) if months_match else 3
                months = min(max(months, 1), 12)  # Clamp 1-12
                
                result = run_demand_forecast_analysis(
                    branch=b,
                    months=months,
                    analysis_type='forecast'
                )
                result['intent'] = 'forecast'
                result['query'] = query
                return JSONResponse(content=_safe_dict(result))
            else:
                return JSONResponse(content={
                    "query": query,
                    "intent": "unknown",
                    "message": (
                        "Query not understood. Try asking about: "
                        "expansion feasibility, branch staffing, or demand forecasting."
                    ),
                    "available_endpoints": [
                        "/expansion",
                        "/staffing/{branch}",
                        "/forecast/demand?branch={branch}&months={n}",
                        "/forecast/all-branches",
                        "/forecast/trends?branch={branch}",
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
        from src.objective_3_expansion import print_report
        print_report(run_expansion_analysis())

        print("\n--- STAFFING ---")
        from src.objective_4_staffing import print_staffing_report
        print_staffing_report(run_staffing_analysis())
        
        print("\n--- DEMAND FORECAST ---")
        from src.objective_2_demand_forecast import print_demand_forecast_report
        print_demand_forecast_report(run_demand_forecast_analysis())
    else:
        import uvicorn
        uvicorn.run(
            "src.api:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info",
        )
