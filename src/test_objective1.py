#!/usr/bin/env python
"""
Quick test script to validate Objective 1 implementation
"""

import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from main import ConutDataProcessor, ComboOptimizer

def test_data_loading():
    """Test if data loads and processes correctly"""
    print("=" * 60)
    print("OBJECTIVE 1: COMBO OPTIMIZATION - DATA VALIDATION")
    print("=" * 60)
    
    try:
        # Initialize processor
        processor = ConutDataProcessor(data_dir=".")
        print("✓ Processor initialized")
        
        # Load data
        df = processor.load_sales_data("REP_S_00502.csv")
        print(f"✓ Data loaded: {len(df)} records")
        print(f"  - Branches: {df['branch'].unique()}")
        print(f"  - Unique products: {len(processor.products)}")
        
        # Initialize optimizer
        optimizer = ComboOptimizer(df)
        print(f"✓ Optimizer initialized")
        print(f"  - Total transactions: {optimizer.total_transactions}")
        
        # Find combos
        combos = optimizer.find_combos(min_support=0.01, min_frequency=2)
        print(f"✓ Combos found: {len(combos)}")
        
        if combos:
            print(f"\nTop 5 Combos:")
            for i, combo in enumerate(combos[:5], 1):
                print(f"  {i}. {' + '.join(combo['products'])}")
                print(f"     Frequency: {combo['frequency']}, Avg Revenue: ${combo['avg_revenue']:.2f}")
        
        # Branch analysis
        branch_combos = optimizer.find_combos_by_branch(min_support=0.01)
        print(f"\n✓ Branch analysis complete:")
        for branch, combos_list in branch_combos.items():
            print(f"  - {branch}: {len(combos_list)} combos")
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED - Ready for FastAPI deployment")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_data_loading()
    sys.exit(0 if success else 1)
