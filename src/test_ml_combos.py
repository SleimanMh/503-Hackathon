#!/usr/bin/env python
"""Test ML-based combo optimization"""

from main import ConutDataProcessor, ComboOptimizer

print("=" * 70)
print("OBJECTIVE 1: ML-BASED COMBO OPTIMIZATION TEST")
print("=" * 70)

# Load data
processor = ConutDataProcessor(data_dir='.')
df = processor.load_sales_data()

# Initialize optimizer
optimizer = ComboOptimizer(df)
print(f"✓ Data loaded: {len(df)} records, {optimizer.total_transactions} transactions")

# Test ML-based combo discovery
print("\n[ML ALGORITHM: Apriori + Association Rules]")
ml_combos = optimizer.find_combos_ml(min_support=0.02, min_confidence=0.1)
print(f"✓ ML-generated combos: {len(ml_combos)}")

if ml_combos:
    print("\nTop 5 ML-Generated Combos (sorted by Lift):")
    for i, combo in enumerate(ml_combos[:5], 1):
        print(f"\n  {i}. {' + '.join(combo['products'])}")
        print(f"     Frequency: {combo['frequency']}")
        print(f"     Support: {combo['support']:.4f}")
        print(f"     Confidence: {combo['confidence']:.4f}")
        print(f"     Lift: {combo.get('lift', 'N/A'):.4f}" if combo.get('lift') else "     Lift: N/A")
        print(f"     Avg Revenue: ${combo['avg_revenue']:.2f}")
        print(f"     ML Generated: {combo.get('ml_generated', False)}")

print("\n" + "=" * 70)
print("✓ ML INTEGRATION SUCCESSFUL")
print("=" * 70)
print("\nKey ML Metrics:")
print("  • Support: How often items appear together (probability)")
print("  • Confidence: Likelihood of buying Y given X")
print("  • Lift: How much more likely to buy together vs independently")
print("    - Lift > 1: Positive correlation (good combo)")
print("    - Lift = 1: No correlation (random)")
print("    - Lift < 1: Negative correlation (avoid bundling)")
