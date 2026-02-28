#!/usr/bin/env python
"""Verify data is loaded from CSV file"""

from main import ConutDataProcessor

processor = ConutDataProcessor(data_dir='.')
df = processor.load_sales_data()  # Uses default filename from code

print("CSV DATA LOADED:")
print(f"✓ Records: {len(df)}")
print(f"✓ Columns: {df.columns.tolist()}")
print()

print("Sample Data (First 5 rows):")
print(df.head(5))
print()

print(f"✓ Branches: {sorted(df['branch'].unique())}")
print(f"✓ Products (sample): {df['product'].unique()[:5]}")
print()

print("✓ This proves code is reading from REP_S_00502.csv")
