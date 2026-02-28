"""
data_loader.py
==============
Robust ingestion and cleaning for all Conut report-style CSVs.
Handles repeated headers, page markers, currency formatting, and anonymised names.
"""
from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from typing import Dict, List

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "app"  # CSVs live in the app/ folder


# ─────────────────────────────────────────────────────────
# Low-level helpers
# ─────────────────────────────────────────────────────────

def _read_csv_rows(path: Path) -> List[List[str]]:
    """Read a CSV file respecting quoted fields (handles commas inside quotes)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return list(csv.reader(io.StringIO(text)))


def _clean_number(val) -> float:
    if val is None or val == "":
        return float("nan")
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return float("nan")


def _is_noise(text: str) -> bool:
    patterns = [
        r"^Conut", r"Copyright", r"www\.omega", r"REP_S_\d+",
        r"Page \d+ of", r"^30-Jan-26", r"Year: 20\d\d", r"From Date:",
        r"PUNCH IN", r"PUNCH OUT", r"Work Duration",
        r"^Time &", r"^Sales by", r"^Summary By", r"^Monthly Sales",
        r"^Average Sales", r"^Tax Report", r"^Customer Orders",
    ]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


# ─────────────────────────────────────────────────────────
# Monthly Sales by Branch  (rep_s_00334_1_SMRY.csv)
# ─────────────────────────────────────────────────────────

MONTH_NUM = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def load_monthly_sales() -> pd.DataFrame:
    """branch | month | month_name | year | revenue"""
    rows = _read_csv_rows(DATA_DIR / "rep_s_00334_1_SMRY.csv")
    records, current_branch = [], None
    for row in rows:
        if not row:
            continue
        first = row[0].strip()
        m = re.match(r"Branch Name:\s*(.+)", first, re.IGNORECASE)
        if m:
            current_branch = m.group(1).strip()
            continue
        if first.lower() in MONTH_NUM and len(row) >= 4:
            try:
                yr = int(row[2].strip()) if row[2].strip().isdigit() else 2025
                rev = _clean_number(row[3])
                if current_branch and not pd.isna(rev):
                    records.append({
                        "branch": current_branch,
                        "month": MONTH_NUM[first.lower()],
                        "month_name": first.capitalize(),
                        "year": yr,
                        "revenue": rev,
                    })
            except Exception:
                pass
    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────
# Average Sales by Menu  (rep_s_00435_SMRY.csv)
# ─────────────────────────────────────────────────────────

KNOWN_BRANCHES = ["Main Street Coffee", "Conut Jnah", "Conut - Tyre", "Conut"]  # longest first to avoid substring mis-match


def load_avg_sales_by_menu() -> pd.DataFrame:
    """branch | menu | num_customers | total_sales | avg_per_customer"""
    rows = _read_csv_rows(DATA_DIR / "rep_s_00435_SMRY.csv")
    records, current_branch = [], None
    for row in rows:
        if not row:
            continue
        first = row[0].strip()
        if first in KNOWN_BRANCHES:
            current_branch = first
            continue
        if not current_branch:
            continue
        if first in ("DELIVERY", "TABLE", "TAKE AWAY") and len(row) >= 4:
            try:
                records.append({
                    "branch": current_branch,
                    "menu": first,
                    "num_customers": _clean_number(row[1]),
                    "total_sales": _clean_number(row[2]),
                    "avg_per_customer": _clean_number(row[3]),
                })
            except Exception:
                pass
    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────
# Tax Summary by Branch  (REP_S_00194_SMRY.csv)
# ─────────────────────────────────────────────────────────

def load_tax_summary() -> pd.DataFrame:
    """branch | vat_revenue | total_revenue"""
    rows = _read_csv_rows(DATA_DIR / "REP_S_00194_SMRY.csv")
    records, current_branch = [], None
    for row in rows:
        if not row:
            continue
        first = row[0].strip()
        m = re.match(r"Branch Name:\s*(.+)", first, re.IGNORECASE)
        if m:
            current_branch = m.group(1).strip()
            continue
        if "Total By Branch" in first and current_branch and len(row) >= 9:
            try:
                records.append({
                    "branch": current_branch,
                    "vat_revenue": _clean_number(row[1]),
                    "total_revenue": _clean_number(row[8]),
                })
            except Exception:
                pass
    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────
# Time & Attendance  (REP_S_00461.csv)
# ─────────────────────────────────────────────────────────

def _parse_duration(s: str) -> float:
    s = s.strip()
    m = re.match(r"(\d+):(\d+):(\d+)", s)
    if m:
        return int(m.group(1)) + int(m.group(2)) / 60 + int(m.group(3)) / 3600
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", s)
    if m:
        return int(m.group(1)) + int(m.group(2)) / 60 + int(m.group(3)) / 3600
    return float("nan")


def _parse_hms(s: str) -> float:
    s = s.strip()
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", s)
    if m:
        return int(m.group(1)) + int(m.group(2)) / 60 + int(m.group(3)) / 3600
    return float("nan")


def load_attendance() -> pd.DataFrame:
    """emp_id | emp_name | branch | date | punch_in_raw | punch_out_raw | duration_hours | shift_start_hour | shift_type"""
    lines = (DATA_DIR / "REP_S_00461.csv").read_text(encoding="utf-8", errors="replace").splitlines()
    records = []
    emp_id = emp_name = branch = None

    for line in lines:
        m = re.search(r"EMP ID\s*:\s*([\d.]+).*?NAME\s*:\s*(\S+)", line, re.IGNORECASE)
        if m:
            emp_id = m.group(1).strip()
            emp_name = m.group(2).strip().rstrip(",")
            branch = None
            continue
        for b in KNOWN_BRANCHES:
            if b in line and line.count(",") >= 3:
                branch = b
                break
        if _is_noise(line) or "Total :" in line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 6 and re.match(r"\d{2}-\w{3}-\d{2}", parts[0]):
            try:
                start = _parse_hms(parts[2])
                dur = _parse_duration(parts[5])
                if start < 6:
                    stype = "Graveyard (00-06)"
                elif start < 12:
                    stype = "Morning (06-12)"
                elif start < 17:
                    stype = "Afternoon (12-17)"
                else:
                    stype = "Evening (17-24)"
                records.append({
                    "emp_id": emp_id, "emp_name": emp_name, "branch": branch,
                    "date": parts[0], "punch_in_raw": parts[2], "punch_out_raw": parts[4],
                    "duration_hours": dur, "shift_start_hour": start, "shift_type": stype,
                })
            except Exception:
                pass

    df = pd.DataFrame(records)
    return df[df["duration_hours"] > 0.1].copy()


# ─────────────────────────────────────────────────────────
# Sales by Items by Group  (rep_s_00191_SMRY.csv)
# ─────────────────────────────────────────────────────────

def load_items_sales() -> pd.DataFrame:
    """branch | division | item | qty | revenue"""
    rows = _read_csv_rows(DATA_DIR / "rep_s_00191_SMRY.csv")
    records = []
    branch = division = None
    skip = ("Total by", "Description", "Branch:", "Division:", "Group:",
            "Sales by", "30-Jan", "Page", "Year:")
    for row in rows:
        if not row:
            continue
        first = row[0].strip()
        m = re.match(r"Branch:\s*(.+)", first, re.IGNORECASE)
        if m:
            branch = m.group(1).strip()
            continue
        m = re.match(r"Division:\s*(.+)", first, re.IGNORECASE)
        if m:
            division = m.group(1).strip()
            continue
        if not first or not branch:
            continue
        if _is_noise(first) or any(first.startswith(p) for p in skip):
            continue
        if len(row) >= 4:
            try:
                rev = _clean_number(row[3])
                if not pd.isna(rev) and rev > 0:
                    records.append({
                        "branch": branch, "division": division,
                        "item": first,
                        "qty": _clean_number(row[2]),
                        "revenue": rev,
                    })
            except Exception:
                pass
    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────
# Customer Orders Delivery  (rep_s_00150.csv)
# ─────────────────────────────────────────────────────────

def load_customer_orders() -> pd.DataFrame:
    """branch | customer | total | num_orders"""
    rows = _read_csv_rows(DATA_DIR / "rep_s_00150.csv")
    records, branch = [], None
    for row in rows:
        if not row:
            continue
        first = row[0].strip()
        if first in KNOWN_BRANCHES:
            branch = first
            continue
        if _is_noise(first) or first in ("Customer Name", "") or first.startswith("Total"):
            continue
        if re.match(r"Person_\d+", first) and len(row) >= 9:
            try:
                records.append({
                    "branch": branch, "customer": first,
                    "total": _clean_number(row[7]),
                    "num_orders": _clean_number(row[8]),
                })
            except Exception:
                pass
    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────
# Summary by Division/Menu  (REP_S_00136_SMRY.csv)
# ─────────────────────────────────────────────────────────

def load_division_summary() -> pd.DataFrame:
    """group | delivery | table | take_away | total"""
    rows = _read_csv_rows(DATA_DIR / "REP_S_00136_SMRY.csv")
    records, header_found = [], False
    for row in rows:
        if not row:
            continue
        joined = ",".join(row)
        if "DELIVERY" in joined and "TABLE" in joined and "TAKE AWAY" in joined:
            header_found = True
            continue
        if not header_found:
            continue
        first = row[0].strip()
        if _is_noise(first) or not first:
            continue
        if len(row) >= 8:
            try:
                group = row[1].strip() if row[0].strip() in ("Conut", "") else first
                total = _clean_number(row[7])
                if group and not group.startswith("Total") and not pd.isna(total) and total > 0:
                    records.append({
                        "group": group,
                        "delivery": _clean_number(row[3]),
                        "table": _clean_number(row[4]),
                        "take_away": _clean_number(row[6]),
                        "total": total,
                    })
            except Exception:
                pass
    df = pd.DataFrame(records)
    if not df.empty:
        df = df.drop_duplicates(subset=["group"])
    return df


# ─────────────────────────────────────────────────────────
# Convenience loader
# ─────────────────────────────────────────────────────────

def load_all() -> Dict[str, pd.DataFrame]:
    return {
        "monthly_sales": load_monthly_sales(),
        "avg_sales_by_menu": load_avg_sales_by_menu(),
        "tax_summary": load_tax_summary(),
        "attendance": load_attendance(),
        "items_sales": load_items_sales(),
        "customer_orders": load_customer_orders(),
        "division_summary": load_division_summary(),
    }


if __name__ == "__main__":
    dfs = load_all()
    for name, df in dfs.items():
        print(f"\n{'='*50}")
        print(f"{name}  shape={df.shape}")
        print(df.head(6).to_string())
