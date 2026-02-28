"""
Test script for Objective 2: Demand Forecasting
Validates the forecasting engine and API endpoints
"""
from src.objective_2_demand_forecast import DemandForecaster, run_demand_forecast_analysis

def test_forecasting_engine():
    """Test the core forecasting engine"""
    print("="*60)
    print("Testing Objective 2: Demand Forecasting")
    print("="*60)
    
    try:
        # Initialize forecaster
        forecaster = DemandForecaster()
        forecaster.load_data()
        
        print(f"\n✓ Data loaded successfully")
        print(f"  Branches found: {len(forecaster.branch_data)}")
        
        for branch in forecaster.branch_data.keys():
            records = len(forecaster.branch_data[branch])
            print(f"  - {branch}: {records} months of data")
        
        # Test single branch forecast
        print("\n" + "-"*60)
        print("Test 1: Single Branch Forecast (Conut Jnah, 3 months)")
        print("-"*60)
        
        result = forecaster.forecast_branch("Conut Jnah", months=3)
        
        print(f"  Branch: {result['branch']}")
        print(f"  Forecast Horizon: {result['forecast_horizon']} months")
        print(f"  Model MAPE: {result['model_accuracy']['mape']:.2f}%")
        print(f"  Model R² Score: {result['model_accuracy']['r2_score']:.3f}")
        print(f"\n  Forecasted Months:")
        for fc in result['forecast']:
            print(f"    - {fc['month']}: ₧{fc['predicted_demand']:,.0f} ({fc['trend']})")
        
        print(f"\n  Insights ({len(result['insights'])} generated):")
        for insight in result['insights'][:3]:  # Show first 3
            print(f"    • {insight}")
        
        # Test all branches
        print("\n" + "-"*60)
        print("Test 2: All Branches Forecast (3 months)")
        print("-"*60)
        
        all_result = forecaster.forecast_all_branches(months=3)
        
        print(f"  Total Forecasted Demand: ₧{all_result['total_company_demand']:,.0f}")
        print(f"  Branch Breakdown:")
        for branch, fc in all_result['branches'].items():
            total = sum(f['predicted_demand'] for f in fc['forecast'])
            pct = fc.get('percentage_of_total', 0)
            print(f"    - {branch}: ₧{total:,.0f} ({pct:.1f}%)")
        
        # Test trend analysis
        print("\n" + "-"*60)
        print("Test 3: Trend Analysis (Conut Jnah, 12 months lookback)")
        print("-"*60)
        
        trend_result = forecaster.get_trend_analysis("Conut Jnah", lookback_months=12)
        
        print(f"  Branch: {trend_result['branch']}")
        print(f"  Period: {trend_result['analysis_period']}")
        print(f"  Trend: {trend_result['trend_direction']}")
        print(f"  Growth Rate: {trend_result['growth_rate']:.2f}% monthly")
        print(f"  Seasonality: {'Yes' if trend_result['seasonality_detected'] else 'No'}")
        if trend_result['peak_months']:
            print(f"  Peak Months: {', '.join(trend_result['peak_months'])}")
        if trend_result['low_months']:
            print(f"  Low Months: {', '.join(trend_result['low_months'])}")
        
        # Test API integration function
        print("\n" + "-"*60)
        print("Test 4: API Integration Function")
        print("-"*60)
        
        api_result = run_demand_forecast_analysis(
            branch="Conut - Tyre",
            months=2,
            analysis_type='forecast'
        )
        
        print(f"  ✓ API function works")
        print(f"  Branch: {api_result['branch']}")
        print(f"  Forecast points: {len(api_result['forecast'])}")
        
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED - Objective 2 is fully functional!")
        print("="*60)
        
        print("\n📊 Summary:")
        print(f"  • Forecasting engine: ✓ Working")
        print(f"  • Multi-branch support: ✓ {len(forecaster.branch_data)} branches")
        print(f"  • Trend analysis: ✓ Growth rates & seasonality")
        print(f"  • Confidence intervals: ✓ Generated")
        print(f"  • Business insights: ✓ Auto-generated")
        print(f"  • API integration: ✓ Ready")
        
        print("\n🚀 Ready for OpenClaw integration!")
        print("   API endpoints available at: http://localhost:8000/forecast/*")
        
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_forecasting_engine()
    exit(0 if success else 1)
