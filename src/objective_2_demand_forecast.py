"""
OBJECTIVE 2: Demand Forecasting by Branch
==========================================
Conut AI Engineering Hackathon

Purpose:
  Forecast demand per branch to support inventory and supply chain decisions.

Status:
  ⚠️ NOT YET IMPLEMENTED - PLACEHOLDER FILE
  
  This objective requires a time series forecasting model using historical
  monthly sales data from rep_s_00334_1_SMRY.csv.

Required Implementation:
  1. Load monthly sa les data (Aug-Dec 2025)
  2. Build forecasting model (Prophet, XGBoost, SARIMA, or LSTM)
  3. Train on historical data
  4. Forecast next 3-6 months per branch
  5. Provide confidence intervals
  6. Calculate evaluation metrics (RMSE, MAE, MAPE)

Expected Output:
  {
    "branch": "Conut Jnah",
    "forecast_months": 6,
    "predictions": [
      {
        "month": "Jan 2026",
        "revenue_forecast": 1234567,
        "confidence_lower": 1100000,
        "confidence_upper": 1350000
      },
      ...
    ],
    "model_type": "Prophet",
    "accuracy_metrics": {
      "mape": 8.5,
      "rmse": 45000,
      "mae": 32000
    }
  }

Recommended Approach:
  - Use Facebook Prophet for seasonality handling
  - Or use XGBoost with lag features for flexibility
  - Include branch-specific models
  - Cross-validate on rolling windows

Data Source:
  - rep_s_00334_1_SMRY.csv (Monthly sales by branch)
  - Available months: August - December 2025 (5 data points per branch)

TODO:
  [ ] Implement load_monthly_sales_for_forecast()
  [ ] Implement train_forecast_model()
  [ ] Implement predict_future_demand()
  [ ] Add model evaluation
  [ ] Integrate with unified API
  [ ] Add unit tests
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Import data loader
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.data_loader import load_monthly_sales


def run_demand_forecast_analysis(months_ahead: int = 6, branch: Optional[str] = None) -> Dict:
    """
    Run demand forecasting analysis (PLACEHOLDER).
    
    Args:
        months_ahead: Number of months to forecast
        branch: Specific branch or None for all branches
    
    Returns:
        Dictionary with forecast results
    """
    # TODO: Implement actual forecasting
    
    # Load historical data
    monthly_sales = load_monthly_sales()
    
    if branch:
        monthly_sales = monthly_sales[monthly_sales['branch'] == branch]
    
    branches = monthly_sales['branch'].unique()
    
    result = {
        "objective": "Demand Forecasting",
        "status": "PLACEHOLDER - NOT YET IMPLEMENTED",
        "branches_analyzed": list(branches),
        "historical_data_points": len(monthly_sales),
        "forecast_months_ahead": months_ahead,
        "note": "This objective requires implementation of time series forecasting model",
        "next_steps": [
            "Choose forecasting algorithm (Prophet recommended)",
            "Train model on historical monthly sales",
            "Generate forecasts with confidence intervals",
            "Validate model performance"
        ]
    }
    
    return result


def print_demand_forecast_report(result: Dict):
    """Print demand forecast report (PLACEHOLDER)."""
    print("\n" + "="*70)
    print("OBJECTIVE 2: DEMAND FORECASTING BY BRANCH")
    print("="*70)
    print(f"\nStatus: {result['status']}")
    print(f"Branches: {', '.join(result['branches_analyzed'])}")
    print(f"Historical data points: {result['historical_data_points']}")
    print(f"Forecast horizon: {result['forecast_months_ahead']} months")
    print(f"\n⚠️ NOTE: {result['note']}")
    print(f"\nNext steps:")
    for step in result['next_steps']:
        print(f"  - {step}")
    print("="*70)


if __name__ == "__main__":
    result = run_demand_forecast_analysis()
    print_demand_forecast_report(result)
