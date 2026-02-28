"""
staffing_engine.py
==================
Shift Staffing Estimation for Conut branches.

Methodology
-----------
Uses Time & Attendance data (REP_S_00461.csv) covering December 2025,
cross-referenced with monthly revenue data and customer volume to build a
data-driven staffing model.

Key Steps
---------
1. Parse all employee punch records per branch.
2. Compute actual shift patterns (shift type distribution, avg shift length,
   unique employees per day, concurrent staff on floor).
3. Derive a "Staff Productivity Index" = Revenue / Staff-Hours per period.
4. Build a demand-driven staffing formula:
     Required Staff = (Expected Customers × Avg Service Time) / Shift Hours
   with a Safety Buffer applied for peak periods.
5. Produce recommendations per shift slot per branch.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.data_loader import load_attendance, load_monthly_sales, load_avg_sales_by_menu


# ─────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────

# Average minutes to serve one customer per channel (assumed industry standard)
SERVICE_TIME_MINS = {
    "TABLE": 35,      # Dine-in service cycle
    "TAKE AWAY": 5,   # Quick counter service
    "DELIVERY": 10,   # Order preparation (kitchen/packing)
}

# Effective working hours in an 8-hour shift (breaks, handovers, admin)
EFFECTIVE_HOURS_PER_SHIFT = 7.0

# Safety buffer multiplier for peak periods (e.g. Fri/Sat evenings)
PEAK_BUFFER = 1.25

# Off-peak reduction
OFF_PEAK_BUFFER = 0.85

# Minimum staff floor per shift (health & safety)
MIN_STAFF = 2


# ─────────────────────────────────────────────────────────
# Attendance Analytics
# ─────────────────────────────────────────────────────────

def compute_attendance_stats(att: pd.DataFrame) -> pd.DataFrame:
    """
    For each branch, compute:
      - total_shifts: number of shift records
      - unique_employees: distinct employees who worked
      - avg_shift_hours: mean duration per shift
      - total_staff_hours: sum of all work hours
      - shift_type_distribution: % of shifts per type
      - avg_concurrent_staff: mean employees working simultaneously per day
      - most_common_shift: most frequent shift slot
    """
    if att.empty:
        return pd.DataFrame()

    rows = []
    for branch, grp in att.groupby("branch"):
        if branch is None:
            continue

        total_shifts = len(grp)
        unique_emp = grp["emp_id"].nunique()
        avg_hours = grp["duration_hours"].mean()
        total_hours = grp["duration_hours"].sum()

        # Shift distribution
        stype_dist = grp["shift_type"].value_counts(normalize=True).to_dict()

        # Avg staff per day (concurrent proxy: unique employees per working date)
        daily_staff = grp.groupby("date")["emp_id"].nunique()
        avg_daily_staff = daily_staff.mean()
        max_daily_staff = daily_staff.max()
        min_daily_staff = daily_staff.min()

        most_common = grp["shift_type"].mode().iloc[0] if not grp.empty else "Unknown"

        rows.append({
            "branch": branch,
            "total_shifts": total_shifts,
            "unique_employees": unique_emp,
            "avg_shift_hours": round(avg_hours, 2),
            "total_staff_hours": round(total_hours, 1),
            "avg_daily_staff": round(avg_daily_staff, 1),
            "max_daily_staff": int(max_daily_staff),
            "min_daily_staff": int(min_daily_staff),
            "most_common_shift": most_common,
            "shift_distribution": stype_dist,
        })

    return pd.DataFrame(rows).set_index("branch")


def compute_shift_profile(att: pd.DataFrame) -> pd.DataFrame:
    """
    Per branch × shift_type:
      - n_shifts, avg_hours, employee_count
    """
    if att.empty:
        return pd.DataFrame()

    grp = att.groupby(["branch", "shift_type"]).agg(
        n_shifts=("duration_hours", "count"),
        avg_hours=("duration_hours", "mean"),
        total_hours=("duration_hours", "sum"),
        unique_employees=("emp_id", "nunique"),
    ).round(2)

    return grp


def compute_productivity_index(
    att_stats: pd.DataFrame,
    monthly_sales: pd.DataFrame,
) -> pd.DataFrame:
    """
    Staff Productivity Index = Monthly Revenue / Total Staff Hours.
    Gives revenue generated per staff-hour — useful for sizing new branches.
    """
    # Use December 2025 revenue (matches attendance period)
    dec = monthly_sales[
        (monthly_sales["month"] == 12) & (monthly_sales["year"] == 2025)
    ].set_index("branch")["revenue"]

    result = []
    for branch in att_stats.index:
        staff_hours = att_stats.loc[branch, "total_staff_hours"]
        rev = dec.get(branch, np.nan)
        if staff_hours > 0 and not np.isnan(rev):
            productivity = rev / staff_hours
        else:
            productivity = np.nan
        result.append({"branch": branch, "dec_revenue": rev,
                        "total_staff_hours": staff_hours,
                        "revenue_per_staff_hour": round(productivity, 0)
                        if not np.isnan(productivity) else np.nan})

    return pd.DataFrame(result).set_index("branch")


# ─────────────────────────────────────────────────────────
# Demand-Driven Staffing Model
# ─────────────────────────────────────────────────────────

def estimate_required_staff(
    branch: str,
    menu_df: pd.DataFrame,
    att_stats: pd.DataFrame,
    peak: bool = False,
) -> Dict:
    """
    Estimate required staff for a given branch based on customer volume,
    service times, and observed shift patterns.

    Parameters
    ----------
    branch      : branch name
    menu_df     : load_avg_sales_by_menu() result
    att_stats   : output of compute_attendance_stats()
    peak        : whether to apply peak buffer

    Returns
    -------
    Dict with recommended staff per shift type
    """
    bm = menu_df[menu_df["branch"] == branch]
    if bm.empty:
        return {"error": f"No menu data for branch: {branch}"}

    # Total annual customers → daily estimate (assume 300 operating days)
    total_annual_cust = bm["num_customers"].sum()
    daily_customers = total_annual_cust / 300.0

    # Channel split
    channel_cust = bm.set_index("menu")["num_customers"].to_dict()
    total_cust = sum(channel_cust.values())

    results = {}
    shift_slots = {
        "Morning (06-12)": 6,
        "Afternoon (12-17)": 5,
        "Evening (17-24)": 7,
        "Graveyard (00-06)": 6,
    }

    # Estimate which channels are active by shift
    # Morning: take-away + delivery heavy
    # Afternoon/Evening: all channels
    # Graveyard: delivery only
    channel_shift_map = {
        "Morning (06-12)":   {"TAKE AWAY": 0.25, "DELIVERY": 0.10, "TABLE": 0.15},
        "Afternoon (12-17)": {"TAKE AWAY": 0.30, "DELIVERY": 0.15, "TABLE": 0.40},
        "Evening (17-24)":   {"TAKE AWAY": 0.30, "DELIVERY": 0.60, "TABLE": 0.35},
        "Graveyard (00-06)": {"TAKE AWAY": 0.05, "DELIVERY": 0.15, "TABLE": 0.10},
    }

    buffer = PEAK_BUFFER if peak else OFF_PEAK_BUFFER

    for shift, shift_hours in shift_slots.items():
        channel_fracs = channel_shift_map[shift]
        total_workload_mins = 0.0

        for channel, frac in channel_fracs.items():
            cust_this_shift = daily_customers * frac
            svc_time = SERVICE_TIME_MINS.get(channel, 10)
            total_workload_mins += cust_this_shift * svc_time

        # Convert to staff needed: workload_hours / effective_hours_per_staff
        workload_hours = total_workload_mins / 60.0
        raw_staff = workload_hours / EFFECTIVE_HOURS_PER_SHIFT
        buffered = raw_staff * buffer
        recommended = max(MIN_STAFF, round(buffered))

        results[shift] = {
            "daily_customers_served": round(daily_customers * sum(channel_shift_map[shift].values()), 1),
            "total_workload_hours": round(workload_hours, 2),
            "recommended_staff": recommended,
            "min_staff": MIN_STAFF,
        }

    return results


def staffing_report_all_branches(
    menu_df: pd.DataFrame,
    att_stats: pd.DataFrame,
) -> Dict[str, Dict]:
    """Run staffing estimation for all branches."""
    branches = menu_df["branch"].unique()
    return {b: estimate_required_staff(b, menu_df, att_stats, peak=False)
            for b in branches}


# ─────────────────────────────────────────────────────────
# Anomaly Detection in Attendance
# ─────────────────────────────────────────────────────────

def detect_staffing_anomalies(att: pd.DataFrame) -> pd.DataFrame:
    """
    Detect anomalous shifts using a scikit-learn IsolationForest model.

    The model is trained unsupervised on two features per shift record:
      - duration_hours   : how long the shift lasted
      - shift_start_hour : hour of day the shift began

    IsolationForest isolates observations by randomly partitioning the
    feature space. Points that require fewer splits to isolate are flagged
    as anomalies (contamination=0.10 → top 10% most isolated = anomalous).

    Additionally, extreme system errors (>25h) are always included regardless
    of the model's decision.
    """
    if att.empty:
        return pd.DataFrame(columns=["emp_id", "branch", "date", "issue", "value", "anomaly_score"])

    # Feature matrix: duration_hours + shift_start_hour
    feature_cols = ["duration_hours", "shift_start_hour"]
    X = att[feature_cols].fillna(0).values.astype(float)

    # Scale features before fitting
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Fit IsolationForest
    iso = IsolationForest(
        n_estimators=100,
        contamination=0.10,   # expect ~10% of shifts to be anomalous
        random_state=42,
        n_jobs=-1,
    )
    iso.fit(X_scaled)

    predictions = iso.predict(X_scaled)        # -1 = anomaly, +1 = normal
    scores = iso.score_samples(X_scaled)       # lower = more anomalous

    flags = []
    for idx, (pred, score) in enumerate(zip(predictions, scores)):
        row = att.iloc[idx]
        issue = None

        if row["duration_hours"] > 25:
            issue = "SYSTEM ERROR (>25h)"
        elif pred == -1:
            # Classify the anomaly type based on the dominant signal
            if row["duration_hours"] > 14:
                issue = "LONG SHIFT"
            elif row["duration_hours"] < 1:
                issue = "SHORT SHIFT / GHOST PUNCH"
            else:
                issue = "UNUSUAL SHIFT PATTERN"

        if issue:
            flags.append({
                "emp_id": row["emp_id"],
                "branch": row["branch"],
                "date": row["date"],
                "issue": issue,
                "value": f"{row['duration_hours']:.1f}h @ {row['shift_type']}",
                "anomaly_score": round(float(score), 4),
            })

    return pd.DataFrame(flags) if flags else pd.DataFrame(
        columns=["emp_id", "branch", "date", "issue", "value", "anomaly_score"]
    )


# ─────────────────────────────────────────────────────────
# Full Pipeline + Report
# ─────────────────────────────────────────────────────────

def run_staffing_analysis() -> Dict:
    att = load_attendance()
    monthly = load_monthly_sales()
    menu = load_avg_sales_by_menu()

    att_stats = compute_attendance_stats(att)
    shift_profile = compute_shift_profile(att)
    productivity = compute_productivity_index(att_stats, monthly)
    staffing = staffing_report_all_branches(menu, att_stats)
    anomalies = detect_staffing_anomalies(att)

    return {
        "attendance_stats": att_stats,
        "shift_profile": shift_profile,
        "productivity_index": productivity,
        "staffing_recommendations": staffing,
        "anomalies": anomalies,
        "raw_attendance": att,
        "ml_anomaly_model": "IsolationForest(n_estimators=100, contamination=0.10)",
    }


def print_staffing_report(result: Dict) -> None:
    sep = "=" * 65
    print(f"\n{sep}")
    print("  CONUT SHIFT STAFFING ESTIMATION REPORT")
    print(sep)

    print("\n[1] Branch Attendance Overview (December 2025)")
    stats = result["attendance_stats"]
    display_cols = ["unique_employees", "total_shifts", "avg_shift_hours",
                    "total_staff_hours", "avg_daily_staff", "max_daily_staff"]
    print(stats[[c for c in display_cols if c in stats.columns]].to_string())

    print("\n[2] Staff Productivity Index (Revenue per Staff-Hour)")
    prod = result["productivity_index"]
    print(prod.to_string())

    print("\n[3] Shift Type Distribution per Branch")
    sp = result["shift_profile"]
    print(sp.to_string())

    print("\n[4] Recommended Staffing per Shift Slot")
    for branch, slots in result["staffing_recommendations"].items():
        print(f"\n  {branch}:")
        if "error" in slots:
            print(f"    {slots['error']}")
            continue
        for shift, rec in slots.items():
            print(f"    {shift:30s}  -> {rec['recommended_staff']} staff  "
                  f"(~{rec['daily_customers_served']} customers, "
                  f"{rec['total_workload_hours']}h workload)")

    anom = result["anomalies"]
    if not anom.empty:
        print(f"\n[5] Attendance Anomalies Detected: {len(anom)}")
        print(f"    Model: {result.get('ml_anomaly_model', 'N/A')}")
        display_cols = [c for c in ["emp_id","branch","date","issue","value","anomaly_score"] if c in anom.columns]
        print(anom[display_cols].to_string(index=False))
    else:
        print("\n[5] No significant attendance anomalies detected.")

    print(sep)


if __name__ == "__main__":
    result = run_staffing_analysis()
    print_staffing_report(result)
