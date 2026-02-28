"""
demand_forecast_engine.py
=========================
Demand Forecasting by Branch for Conut.

Methodology
-----------
Uses monthly revenue data from rep_s_00334_1_SMRY.csv (Aug–Dec 2025)
and extrapolates forward using three complementary approaches:

1. Linear Regression — OLS trend line per branch (sklearn / numpy).
2. Exponential Smoothing — captures multiplicative growth patterns.
3. Holt's Linear Trend (double exponential smoothing) — handles both
   level and trend, ideal for short non-seasonal series.

For each branch we produce:
  - Jan / Feb / Mar 2026 point forecasts
  - 80% and 95% prediction intervals (based on residual std)
  - Growth trajectory classification (Accelerating / Stable / Decelerating)
  - Inventory / supply chain actionable signals

Cross-branch signals:
  - Network-wide demand index
  - Branch share forecasts
  - Peak-month probability distribution
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.data_loader import load_monthly_sales


# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────

def _holt_forecast(
    values: np.ndarray,
    alpha: float = 0.8,
    beta: float = 0.2,
    h: int = 3,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Holt's Double Exponential Smoothing.
    Returns (forecasts, smoothed_values).
    alpha = level smoothing, beta = trend smoothing.
    """
    n = len(values)
    level = np.zeros(n)
    trend = np.zeros(n)

    level[0] = values[0]
    trend[0] = values[1] - values[0] if n > 1 else 0.0

    for t in range(1, n):
        level[t] = alpha * values[t] + (1 - alpha) * (level[t - 1] + trend[t - 1])
        trend[t] = beta * (level[t] - level[t - 1]) + (1 - beta) * trend[t - 1]

    forecasts = np.array([level[-1] + (i + 1) * trend[-1] for i in range(h)])
    return forecasts, level + trend


def _linear_forecast(
    x: np.ndarray,
    y: np.ndarray,
    future_x: np.ndarray,
    confidence: float = 0.80,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    """
    OLS linear regression forecast with prediction intervals.
    Returns (y_pred, lower_ci, upper_ci, slope, r_squared).
    """
    slope, intercept, r, p, se = scipy_stats.linregress(x, y)
    y_pred = slope * future_x + intercept

    # Prediction interval
    n = len(x)
    x_mean = x.mean()
    s_err = np.sqrt(np.sum((y - (slope * x + intercept)) ** 2) / (n - 2)) if n > 2 else 0.0
    t_val = scipy_stats.t.ppf((1 + confidence) / 2, df=n - 2) if n > 2 else 1.28

    margin = t_val * s_err * np.sqrt(
        1 + 1 / n + (future_x - x_mean) ** 2 / np.sum((x - x_mean) ** 2 + 1e-12)
    )

    return y_pred, y_pred - margin, y_pred + margin, float(slope), float(r ** 2)


def _exp_forecast(values: np.ndarray, h: int = 3) -> np.ndarray:
    """Simple exponential extrapolation based on CAGR."""
    if len(values) < 2 or values[0] <= 0:
        return np.full(h, values[-1] if values.size else 0.0)
    cagr = (values[-1] / values[0]) ** (1 / (len(values) - 1)) - 1
    # Dampen extreme growth to avoid absurd projections
    cagr = min(cagr, 1.5)  # cap at 150% per month
    return np.array([values[-1] * (1 + cagr) ** (i + 1) for i in range(h)])


# ─────────────────────────────────────────────────────────
# Per-Branch Forecast
# ─────────────────────────────────────────────────────────

FORECAST_MONTHS = ["January 2026", "February 2026", "March 2026"]
FORECAST_MONTH_NUMS = [1, 2, 3]  # month index offsets from Dec 2025


def forecast_branch(branch: str, monthly_df: pd.DataFrame) -> Dict:
    """
    Generate a 3-month forecast for a single branch.
    """
    bdf = monthly_df[monthly_df["branch"] == branch].sort_values("month")
    if len(bdf) < 2:
        return {"error": f"Insufficient data for {branch} (< 2 months)"}

    y = bdf["revenue"].values.astype(float)
    x = np.arange(1, len(y) + 1, dtype=float)
    future_x = np.arange(len(y) + 1, len(y) + 4, dtype=float)

    # --- Model 1: Linear ---
    lin_pred, lin_lo, lin_hi, lin_slope, lin_r2 = _linear_forecast(x, y, future_x)

    # --- Model 2: Holt Double Exponential ---
    holt_pred, holt_smoothed = _holt_forecast(y, alpha=0.8, beta=0.2, h=3)

    # --- Model 3: Exponential Extrapolation ---
    exp_pred = _exp_forecast(y, h=3)

    # --- Ensemble: weighted average (Holt 50%, Linear 30%, Exp 20%) ---
    ensemble = 0.50 * holt_pred + 0.30 * lin_pred + 0.20 * exp_pred
    ensemble = np.maximum(ensemble, 0)  # no negative revenue

    # --- Prediction interval from residual std of Holt ---
    fitted_resid = y - holt_smoothed[:len(y)]
    resid_std = np.std(fitted_resid) if len(fitted_resid) > 1 else y.std() * 0.1
    z80 = 1.28
    z95 = 1.96
    lower_80 = ensemble - z80 * resid_std
    upper_80 = ensemble + z80 * resid_std
    lower_95 = ensemble - z95 * resid_std
    upper_95 = ensemble + z95 * resid_std

    # Classify trajectory
    growth_6m = (y[-1] / y[0] - 1) if y[0] > 0 else 0.0
    if growth_6m > 0.5:
        trajectory = "Strongly Accelerating"
    elif growth_6m > 0.1:
        trajectory = "Growing"
    elif growth_6m > -0.1:
        trajectory = "Stable"
    else:
        trajectory = "Declining"

    # Supply chain signal
    peak_rev = y.max()
    dec_rev = y[-1]
    inventory_signal = (
        "SCALE UP — momentum suggests Q1 demand spike" if trajectory in ("Strongly Accelerating", "Growing")
        else ("HOLD — stable demand expected" if trajectory == "Stable"
              else "REDUCE — declining trend; avoid overstock")
    )

    return {
        "branch": branch,
        "historical_months": bdf["month_name"].tolist(),
        "historical_revenue": y.tolist(),
        "trajectory": trajectory,
        "monthly_growth_rate_hist": round(float((y[-1] / y[0]) ** (1 / (len(y) - 1)) - 1) * 100, 2),
        "r_squared_linear": round(lin_r2, 3),
        "forecast_months": FORECAST_MONTHS,
        "forecast_ensemble": [round(v, 0) for v in ensemble.tolist()],
        "forecast_linear": [round(v, 0) for v in lin_pred.tolist()],
        "forecast_holt": [round(v, 0) for v in holt_pred.tolist()],
        "forecast_exp": [round(v, 0) for v in exp_pred.tolist()],
        "lower_80": [round(max(v, 0), 0) for v in lower_80.tolist()],
        "upper_80": [round(v, 0) for v in upper_80.tolist()],
        "lower_95": [round(max(v, 0), 0) for v in lower_95.tolist()],
        "upper_95": [round(v, 0) for v in upper_95.tolist()],
        "inventory_signal": inventory_signal,
        "peak_historical_revenue": round(float(peak_rev), 0),
        "dec_2025_revenue": round(float(dec_rev), 0),
    }


# ─────────────────────────────────────────────────────────
# Network-Level Demand Index
# ─────────────────────────────────────────────────────────

def compute_network_demand(monthly_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregated network revenue per month + growth metrics.
    """
    network = (
        monthly_df.groupby(["month", "month_name", "year"])["revenue"]
        .sum()
        .reset_index()
        .sort_values("month")
    )
    base = network["revenue"].iloc[0]
    network["demand_index"] = (network["revenue"] / base * 100).round(1)
    network["mom_growth_pct"] = network["revenue"].pct_change().round(4) * 100
    return network


def compute_branch_share(monthly_df: pd.DataFrame) -> pd.DataFrame:
    """
    Per-branch revenue share per month (% of network total).
    """
    totals = monthly_df.groupby("month")["revenue"].transform("sum")
    df = monthly_df.copy()
    df["share_pct"] = (df["revenue"] / totals * 100).round(2)
    return df[["branch", "month", "month_name", "revenue", "share_pct"]]


# ─────────────────────────────────────────────────────────
# Master Runner
# ─────────────────────────────────────────────────────────

def run_demand_forecast() -> Dict:
    """Full demand forecasting pipeline."""
    monthly = load_monthly_sales()
    branches = monthly["branch"].unique()

    forecasts = {}
    for branch in branches:
        forecasts[branch] = forecast_branch(branch, monthly)

    network = compute_network_demand(monthly)
    branch_share = compute_branch_share(monthly)

    # Network 3-month forecast (sum of branch ensembles)
    net_forecast = np.zeros(3)
    for fc in forecasts.values():
        if "forecast_ensemble" in fc:
            net_forecast += np.array(fc["forecast_ensemble"])

    return {
        "forecasts": forecasts,
        "network_monthly": network,
        "branch_share": branch_share,
        "network_forecast_3m": net_forecast.tolist(),
        "forecast_months": FORECAST_MONTHS,
    }


def print_forecast_report(result: Dict) -> None:
    print("\n" + "=" * 65)
    print("  CONUT — DEMAND FORECAST REPORT (Jan-Mar 2026)")
    print("=" * 65)

    network = result["network_monthly"]
    print("\n[1] NETWORK MONTHLY DEMAND INDEX")
    for _, r in network.iterrows():
        bar = "#" * int(r["demand_index"] / 5)
        print(f"  {r['month_name']:>10} {r['year']}: {r['revenue']:>20,.0f}  "
              f"[{r['demand_index']:>6.1f}]  {bar}")

    print(f"\n[2] BRANCH FORECASTS — 3-MONTH OUTLOOK")
    for branch, fc in result["forecasts"].items():
        if "error" in fc:
            print(f"\n  {branch}: {fc['error']}")
            continue
        print(f"\n  {branch}")
        print(f"    Trajectory   : {fc['trajectory']}")
        print(f"    Hist. CMGR   : {fc['monthly_growth_rate_hist']:+.1f}%/month")
        print(f"    R-squared    : {fc['r_squared_linear']:.3f}")
        print(f"    Signal       : {fc['inventory_signal']}")
        print(f"    {'Month':<20} {'Forecast':>15} {'80% CI':>25}")
        for i, month in enumerate(fc["forecast_months"]):
            ci = f"[{fc['lower_80'][i]:>15,.0f} - {fc['upper_80'][i]:<15,.0f}]"
            print(f"    {month:<20} {fc['forecast_ensemble'][i]:>15,.0f}  {ci}")

    net_fc = result["network_forecast_3m"]
    print(f"\n[3] NETWORK-WIDE FORECAST")
    for i, m in enumerate(result["forecast_months"]):
        print(f"  {m:<20}: {net_fc[i]:>20,.0f}")

    print("\n" + "=" * 65)


if __name__ == "__main__":
    result = run_demand_forecast()
    print_forecast_report(result)
