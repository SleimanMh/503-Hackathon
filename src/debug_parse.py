#!/usr/bin/env python
"""Debug CSV parsing"""

with open("REP_S_00502.csv", 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Manual parsing test
records = []
current_branch = None
current_customer = None

print("=== PARSING DEBUG ===\n")

for i, line in enumerate(lines[:100]):
    line_raw = line.rstrip('\n')
    
    # Test branch detection
    if line_raw.strip().startswith("Branch :"):
        branch = line_raw.replace("Branch :", "").split(",")[0].strip()
        print(f"Line {i}: Found BRANCH: '{branch}'")
        current_branch = branch
        
    # Test customer detection  
    parts = line_raw.split(",")
    if parts[0] and "Person_" in parts[0] and not line_raw.startswith(" "):
        print(f"Line {i}: Found CUSTOMER: '{parts[0].strip()}'")
        current_customer = parts[0].strip()
        
    # Test item detection
    if line_raw.startswith(",") and "Person_" not in line_raw and i > 5:
        fields = [p.strip() for p in line_raw.split(",")]
        if len(fields) >= 4:
            print(f"Line {i}: ITEM: qty={fields[0]}, desc={fields[2] if len(fields) > 2 else 'N/A'}, price={fields[3] if len(fields) > 3 else 'N/A'}")
