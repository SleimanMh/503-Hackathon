"""
OBJECTIVE 5: Coffee and Milkshake Growth Strategy
Conut AI Engineering Hackathon

Purpose:
  Develop data-driven strategies to increase coffee and milkshake sales
  by analyzing customer segments, preferences, and growth opportunities.

Output Location:
  - API Endpoint: /api/growth-recommendations
  - Report: 05_Growth_Strategy.pdf (generated)
  - Dashboard: Real-time metrics on OpenClaw agent
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import re
import csv

# ============================================================================
# CONFIGURATION
# ============================================================================

REFERENCE_DATE = datetime(2025, 12, 31)

# Define product categories (from rep_s_00191_SMRY.csv)
COFFEE_PRODUCTS = [
    'AMERICAN COFFEE', 'CAPPUCCINO', 'CAFFE LATTE', 'CAFE MOCHA',
    'CARAMEL MACHIATO', 'CAFFE AMERICANO', 'SINGLE ESPRESSO',
    'DOUBLE ESPRESSO', 'ESPRESSO MACCHIATO', 'WHITE MOCHA',
    'FLAT WHITE', 'HOT CHOCOLATE COMBO'
]

MILKSHAKE_PRODUCTS = [
    'VANILLA MILKSHAKE', 'OREO MILKSHAKE', 'STRAWBERRY MILKSHAKE',
    'MATCHA MILKSHAKE', 'SALTED CARAMEL MILKSHAKE', 'PISTACHIO MILKSHAKE',
    'GRANOLA BERRIES MILKSHAKE', 'DOUBLE CHOCOLATE MILKSHAKE',
    'FRUIT LOOPS MILKSHAKE', 'TOFFEE NUT MILKSHAKE'
]

FRAPPE_PRODUCTS = [
    'MOCHA FRAPPE', 'CARAMEL MOCHA FRAPPE', 'HAZELNUT MOCHA FRAPPE',
    'CARAMEL FRAPPE', 'VANILLA FRAPPE', 'WHITE MOCHA FRAPPE',
    'HAZELNUT FRAPPE', 'MATCHA FRAPPE', 'SALTED CARAMEL FRAPPE',
    'ESPRESSO FRAPPE', 'TOFFEE NUT FRAPPE'
]

# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================

def clean_numeric(value):
    """Convert string with commas to float"""
    if pd.isna(value) or value == '':
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    # Remove commas and quotes
    cleaned = str(value).replace(',', '').replace('"', '').strip()
    try:
        return float(cleaned)
    except:
        return 0.0

def load_products_by_division(filepath='rep_s_00191_SMRY.csv'):
    """
    Load and parse product sales data from rep_s_00191_SMRY.csv
    Extracts division-level totals and individual products
    """
    print(f"Loading product data from {filepath}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        lines = list(reader)
    
    data = []
    current_branch = None
    current_division = None
    current_group = None
    
    for i, parts in enumerate(lines):
        parts = [p.strip() for p in parts]
        
        # Check for branch header with "Branch: " prefix
        if len(parts) > 0 and parts[0].startswith('Branch:'):
            current_branch = parts[0].replace('Branch:', '').strip()
            print(f"  Found branch: {current_branch}")
        
        # Division header
        elif len(parts) > 0 and parts[0].startswith('Division:'):
            current_division = parts[0].replace('Division:', '').strip()
        
        # Group header
        elif len(parts) > 0 and parts[0].startswith('Group:'):
            current_group = parts[0].replace('Group:', '').strip()
        
        # Division total line
        elif len(parts) > 0 and parts[0].startswith('Total by Division:'):
            division_name = parts[0].replace('Total by Division:', '').strip()
            if len(parts) >= 4:
                qty = clean_numeric(parts[2])
                amount = clean_numeric(parts[3])
                if amount > 0:  # Only add non-zero totals
                    data.append({
                        'branch': current_branch,
                        'division': division_name,
                        'group': None,
                        'product': f'TOTAL_{division_name}',
                        'qty': qty,
                        'amount': amount,
                        'is_total': True
                    })
        
        # Product line (has product name and numeric data)
        elif len(parts) >= 4 and parts[0] and not parts[0].startswith('Total') and not parts[0].startswith('Division') and not parts[0].startswith('Group') and not parts[0].startswith('30-Jan') and not parts[0].startswith('REP_') and not parts[0].startswith('Branch') and parts[0] != 'Description':
            product_name = parts[0]
            qty = clean_numeric(parts[2] if len(parts) > 2 else 0)
            amount = clean_numeric(parts[3] if len(parts) > 3 else 0)
            
            if product_name and (qty > 0 or amount > 0):
                data.append({
                    'branch': current_branch,
                    'division': current_division,
                    'group': current_group,
                    'product': product_name,
                    'qty': qty,
                    'amount': amount,
                    'is_total': False
                })
    
    df = pd.DataFrame(data)
    print(f"  * Loaded {len(df)} product records")
    print(f"  * Branches: {df['branch'].nunique()}")
    print(f"  * Divisions: {df['division'].nunique()}")
    
    # Show total ITEMS revenue per branch
    items_by_branch = df[(df['is_total'] == True) & (df['division'] == 'ITEMS')].groupby('branch')['amount'].sum()
    print(f"  * Total ITEMS revenue by branch:")
    for branch, amount in items_by_branch.items():
        print(f"      {branch}: {amount:,.0f}")
    
    return df

def load_customers(filepath='rep_s_00150.csv'):
    """
    Load customer data from rep_s_00150.csv
    """
    print(f"Loading customer data from {filepath}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        lines = list(reader)
    
    data = []
    current_branch = None
    
    for parts in lines:
        parts = [p.strip() for p in parts]
        
        # Branch line (appears before customer data)
        branch_keywords = ['Conut - Tyre', 'Conut', 'Conut Jnah', 'Main Street Coffee']
        if len(parts) > 0:
            for keyword in branch_keywords:
                if parts[0] == keyword and 'Customer Orders' not in str(parts):
                    current_branch = parts[0]
                    print(f"  Found branch: {current_branch}")
                    break
        
        # Customer data line
        if len(parts) >= 8 and parts[0].startswith('Person_'):
            customer_name = parts[0]
            phone = parts[2] if len(parts) > 2 else ''
            first_order = parts[3] if len(parts) > 3 else ''
            last_order = parts[5] if len(parts) > 5 else ''
            total = clean_numeric(parts[7] if len(parts) > 7 else 0)
            num_orders = int(clean_numeric(parts[8] if len(parts) > 8 else 1))
            
            # Calculate days since last order
            days_since = 0
            if last_order:
                try:
                    last_date = datetime.strptime(last_order.split()[0], '%Y-%m-%d')
                    days_since = (REFERENCE_DATE - last_date).days
                except:
                    days_since = 365
            
            if total > 0 or num_orders > 0:  # Only add customers with data
                data.append({
                    'customer': customer_name,
                    'branch': current_branch,
                    'phone': phone,
                    'first_order': first_order,
                    'last_order': last_order,
                    'lifetime_value': total,
                    'order_count': num_orders,
                    'days_since_last_order': days_since
                })
    
    df = pd.DataFrame(data)
    print(f"  * Loaded {len(df)} customers")
    print(f"  * Total customer lifetime value: {df['lifetime_value'].sum():,.0f}")
    print(f"  * Average orders per customer: {df['order_count'].mean():.1f}")
    
    return df

# ============================================================================
# STEP 1: DATA ANALYSIS
# ============================================================================

class CoffeeAndMilkshakeAnalysis:
    """Analyze coffee and milkshake sales patterns using REAL data"""
    
    def __init__(self, products_df, customers_df):
        """
        Initialize with cleaned datasets
        
        Args:
            products_df: Product sales data from rep_s_00191_SMRY.csv
            customers_df: Customer master file from rep_s_00150.csv
        """
        self.products = products_df
        self.customers = customers_df
        self.insights = {}
    
    def current_state_analysis(self):
        """Analyze current coffee + milkshake performance using REAL data"""
        
        # Get division totals (these are the accurate aggregates)
        division_totals = self.products[self.products['is_total'] == True].copy()
        
        # Calculate coffee revenue (Hot-Coffee Based + Frappes)
        coffee_divisions = division_totals[
            division_totals['division'].isin(['Hot-Coffee Based', 'Frappes'])
        ]
        coffee_revenue = coffee_divisions['amount'].sum()
        
        # Calculate milkshake revenue (Shakes division)
        milkshake_divisions = division_totals[
            division_totals['division'] == 'Shakes'
        ]
        milkshake_revenue = milkshake_divisions['amount'].sum()
        
        # Total company revenue from ITEMS division (the main revenue)
        items_totals = division_totals[division_totals['division'] == 'ITEMS']
        total_company_revenue = items_totals['amount'].sum()
        
        # If ITEMS not found, sum all divisions
        if total_company_revenue == 0:
            total_company_revenue = division_totals['amount'].sum()
        
        coffee_pct = (coffee_revenue / total_company_revenue) * 100 if total_company_revenue > 0 else 0
        milkshake_pct = (milkshake_revenue / total_company_revenue) * 100 if total_company_revenue > 0 else 0
        
        # Get top-selling products
        coffee_products = self.products[
            (self.products['is_total'] == False) & 
            (self.products['product'].isin(COFFEE_PRODUCTS + FRAPPE_PRODUCTS))
        ].nlargest(5, 'amount')
        
        milkshake_products = self.products[
            (self.products['is_total'] == False) & 
            (self.products['product'].isin(MILKSHAKE_PRODUCTS))
        ].nlargest(5, 'amount')
        
        self.insights['current_state'] = {
            'coffee_revenue': float(coffee_revenue),
            'coffee_pct_of_total': float(coffee_pct),
            'coffee_status': 'UNDERPERFORMING' if coffee_pct < 10 else 'STABLE',
            'milkshake_revenue': float(milkshake_revenue),
            'milkshake_pct_of_total': float(milkshake_pct),
            'milkshake_status': 'UNDERPERFORMING' if milkshake_pct < 10 else 'STABLE',
            'combined_pct': float(coffee_pct + milkshake_pct),
            'total_revenue': float(total_company_revenue),
            'top_coffee_products': coffee_products[['product', 'amount', 'qty']].to_dict('records'),
            'top_milkshake_products': milkshake_products[['product', 'amount', 'qty']].to_dict('records')
        }
        
        print("=" * 70)
        print("CURRENT STATE ANALYSIS (REAL DATA)")
        print("=" * 70)
        print(f"\nTotal Company Revenue: {total_company_revenue:,.0f}")
        print(f"\nCoffee Category (Hot Coffee + Frappes): {coffee_pct:.1f}% of total revenue")
        print(f"  Revenue: {coffee_revenue:,.0f}")
        print(f"  Status: {self.insights['current_state']['coffee_status']}")
        print(f"\n  Top 3 Coffee Products:")
        for prod in coffee_products.head(3).itertuples():
            print(f"    • {prod.product}: {prod.amount:,.0f} ({prod.qty:.0f} units)")
        
        print(f"\nMilkshake Category: {milkshake_pct:.1f}% of total revenue")
        print(f"  Revenue: {milkshake_revenue:,.0f}")
        print(f"  Status: {self.insights['current_state']['milkshake_status']}")
        print(f"\n  Top 3 Milkshake Products:")
        for prod in milkshake_products.head(3).itertuples():
            print(f"    • {prod.product}: {prod.amount:,.0f} ({prod.qty:.0f} units)")
        
        print(f"\nCombined: {coffee_pct + milkshake_pct:.1f}% of revenue")
        print(f"Growth Opportunity: Can increase from {coffee_pct + milkshake_pct:.1f}% to higher market share")
        
        return self.insights['current_state']
    
    def customer_segment_analysis(self):
        """Identify high-value customer segments from REAL data"""
        
        if self.customers is None or len(self.customers) == 0:
            print("WARNING: Customer data not available for segmentation")
            return None
        
        # Calculate actual statistics
        total_customers = len(self.customers)
        avg_order_value = self.customers['lifetime_value'].mean()
        avg_order_count = self.customers['order_count'].mean()
        
        # Segment 1: High Frequency (3+ orders)
        high_freq = self.customers[self.customers['order_count'] >= 3]
        high_freq_revenue = high_freq['lifetime_value'].sum()
        
        # Segment 2: High Value (top 25% by lifetime value)
        high_value_threshold = self.customers['lifetime_value'].quantile(0.75)
        high_value = self.customers[self.customers['lifetime_value'] >= high_value_threshold]
        high_value_revenue = high_value['lifetime_value'].sum()
        
        # Segment 3: Active (ordered in last 30 days)
        active = self.customers[self.customers['days_since_last_order'] <= 30]
        active_revenue = active['lifetime_value'].sum()
        
        # Segment 4: At Risk (haven't ordered in 90+ days but have 2+ orders)
        at_risk = self.customers[
            (self.customers['days_since_last_order'] > 90) &
            (self.customers['order_count'] >= 2)
        ]
        at_risk_potential = at_risk['lifetime_value'].sum()
        
        self.insights['segments'] = {
            'high_frequency': {
                'count': int(len(high_freq)),
                'pct_of_customers': float((len(high_freq) / total_customers) * 100),
                'avg_order_value': float(high_freq['lifetime_value'].mean()) if len(high_freq) > 0 else 0,
                'total_revenue': float(high_freq_revenue),
                'avg_orders': float(high_freq['order_count'].mean()) if len(high_freq) > 0 else 0,
                'description': 'Orders 3+ times (loyal base)'
            },
            'high_value': {
                'count': int(len(high_value)),
                'pct_of_customers': float((len(high_value) / total_customers) * 100),
                'avg_order_value': float(high_value['lifetime_value'].mean()) if len(high_value) > 0 else 0,
                'total_revenue': float(high_value_revenue),
                'avg_orders': float(high_value['order_count'].mean()) if len(high_value) > 0 else 0,
                'description': 'Top 25% spenders (premium customers)'
            },
            'active': {
                'count': int(len(active)),
                'pct_of_customers': float((len(active) / total_customers) * 100),
                'avg_order_value': float(active['lifetime_value'].mean()) if len(active) > 0 else 0,
                'total_revenue': float(active_revenue),
                'avg_orders': float(active['order_count'].mean()) if len(active) > 0 else 0,
                'description': 'Recent purchasers (last 30 days)'
            },
            'at_risk': {
                'count': int(len(at_risk)),
                'pct_of_customers': float((len(at_risk) / total_customers) * 100),
                'avg_order_value': float(at_risk['lifetime_value'].mean()) if len(at_risk) > 0 else 0,
                'potential_recovery': float(at_risk_potential),
                'avg_orders': float(at_risk['order_count'].mean()) if len(at_risk) > 0 else 0,
                'description': 'Loyal customers who stopped ordering (win-back opportunity)'
            }
        }
        
        print("\n" + "=" * 70)
        print("CUSTOMER SEGMENT ANALYSIS (REAL DATA)")
        print("=" * 70)
        print(f"\nTotal Customers: {total_customers:,}")
        print(f"Average Lifetime Value: {avg_order_value:,.0f}")
        print(f"Average Orders per Customer: {avg_order_count:.1f}")
        
        for segment_name, segment_data in self.insights['segments'].items():
            print(f"\n{segment_name.upper().replace('_', ' ')}:")
            print(f"  Count: {segment_data['count']:,} customers "
                  f"({segment_data['pct_of_customers']:.1f}%)")
            print(f"  Avg lifetime value: {segment_data['avg_order_value']:,.0f}")
            if 'total_revenue' in segment_data:
                print(f"  Total revenue: {segment_data['total_revenue']:,.0f}")
            if 'potential_recovery' in segment_data:
                print(f"  Win-back potential: {segment_data['potential_recovery']:,.0f}")
            print(f"  → {segment_data['description']}")
        
        return self.insights['segments']
    
    def growth_opportunity_analysis(self):
        """Identify top 3 growth opportunities based on REAL DATA patterns"""
        
        current = self.insights.get('current_state', {})
        segments = self.insights.get('segments', {})
        
        coffee_pct = current.get('coffee_pct_of_total', 0)
        milkshake_pct = current.get('milkshake_pct_of_total', 0)
        
        # Calculate potential based on actual data
        high_freq_pct = segments.get('high_frequency', {}).get('pct_of_customers', 0)
        at_risk_count = segments.get('at_risk', {}).get('count', 0)
        at_risk_potential = segments.get('at_risk', {}).get('potential_recovery', 0)
        
        opportunities = [
            {
                'id': 1,
                'name': 'Loyalty Program for Repeat Customers',
                'target_segment': f'High Frequency customers ({int(high_freq_pct)}% of customer base)',
                'strategy': 'Coffee/Milkshake subscription: "10th drink free" program',
                'current_adoption': '0%',
                'potential_adoption': '40-60%',
                'growth_potential': f'+{min(35, int(high_freq_pct * 0.5))}% coffee sales',
                'data_insight': f'{int(high_freq_pct)}% of customers order 3+ times - high loyalty potential',
                'timeline': '1 month (app setup + marketing)',
                'cost': 'Low (discount absorbed by volume increase)',
                'implementation': [
                    'Set up digital loyalty tracking system',
                    'Target social media ads to existing customer base',
                    'Partner with universities/offices nearby',
                    'Staff training on loyalty upsell at checkout'
                ]
            },
            {
                'id': 2,
                'name': 'Win-Back Campaign for Lapsed Customers',
                'target_segment': f'{at_risk_count} customers who stopped ordering (recovery opportunity)',
                'strategy': 'Personalized "We miss you" offer: 25% off next coffee/milkshake order',
                'current_adoption': '0%',
                'potential_adoption': '15-25%',
                'growth_potential': f'+{int((at_risk_potential / current.get("total_revenue", 1)) * 100 * 0.2)}% revenue recovery',
                'data_insight': f'{at_risk_count} at-risk customers represent {at_risk_potential:,.0f} in past revenue',
                'timeline': '2 weeks (email/SMS campaign)',
                'cost': 'Low (discount on single order)',
                'implementation': [
                    'Segment customers by days since last order (90+ days)',
                    'Send personalized SMS/email with 25% off code',
                    'Track response rate and repeat purchase',
                    'Enroll recovered customers in loyalty program'
                ]
            },
            {
                'id': 3,
                'name': 'Premium Milkshake Variants',
                'target_segment': 'High-value customers (top 25% spenders)',
                'strategy': 'Launch premium line: Protein milkshakes, seasonal flavors',
                'current_adoption': '0%',
                'potential_adoption': '20-30%',
                'growth_potential': f'+{int(milkshake_pct * 0.35)}% milkshake sales',
                'data_insight': f'Top products: {", ".join([p["product"] for p in current.get("top_milkshake_products", [])[:2]])}',
                'timeline': '3 months (recipe development + testing)',
                'cost': 'Medium (ingredient sourcing, menu updates)',
                'implementation': [
                    'Survey high-value customers on preferences',
                    'Develop 3-5 premium variants (protein, low-sugar, seasonal)',
                    'Test with focus group of top customers',
                    'Price 20-30% higher than standard milkshakes',
                    'Launch with influencer marketing campaign'
                ]
            }
        ]
        
        self.insights['opportunities'] = opportunities
        
        print("\n" + "=" * 70)
        print("TOP 3 GROWTH OPPORTUNITIES (DATA-BACKED)")
        print("=" * 70)
        
        for opp in opportunities:
            print(f"\n#{opp['id']}: {opp['name'].upper()}")
            print(f"  Target: {opp['target_segment']}")
            print(f"  Strategy: {opp['strategy']}")
            print(f"  Data Insight: {opp['data_insight']}")
            print(f"  Potential adoption: {opp['potential_adoption']}")
            print(f"  Growth potential: {opp['growth_potential']}")
            print(f"  Timeline: {opp['timeline']}")
            print(f"  Cost: {opp['cost']}")
            print(f"  Implementation steps:")
            for step in opp['implementation']:
                print(f"    • {step}")
        
        return opportunities
    
    def revenue_projection(self):
        """Project 12-month revenue impact based on REAL data"""
        
        current = self.insights['current_state']
        opportunities = self.insights.get('opportunities', [])
        
        # Extract growth rates from opportunities
        growth_factors = []
        for opp in opportunities:
            # Parse growth potential (e.g., "+35% coffee sales" -> 0.35)
            growth_str = opp['growth_potential']
            match = re.search(r'\+(\d+)%', growth_str)
            if match:
                growth_factors.append(float(match.group(1)) / 100)
        
        # Be conservative: Not all strategies will be fully successful
        # Assume: 60% adoption of strategy 1, 20% of strategy 2, 40% of strategy 3
        implementation_rates = [0.60, 0.20, 0.40]
        
        # Calculate cumulative impact
        coffee_base = current['coffee_pct_of_total']
        milkshake_base = current['milkshake_pct_of_total']
        
        # Base projections
        projections = {
            'month_0': {
                'coffee_pct': coffee_base,
                'milkshake_pct': milkshake_base,
                'combined_pct': coffee_base + milkshake_base
            }
        }
        
        # Growth trajectory (gradual rollout)
        months = ['month_1', 'month_3', 'month_6', 'month_12']
        time_factors = [0.10, 0.30, 0.60, 1.00]  # Implementation progress
        
        for i, (month, time_factor) in enumerate(zip(months, time_factors)):
            # Calculate cumulative lift
            total_coffee_lift = 0
            total_milkshake_lift = 0
            
            for j, (growth_rate, impl_rate) in enumerate(zip(growth_factors, implementation_rates)):
                realized_growth = growth_rate * impl_rate * time_factor
                
                # Strategy 1: Coffee focused
                if j == 0:
                    total_coffee_lift += realized_growth
                # Strategy 2: Mixed (helps both)
                elif j == 1:
                    total_coffee_lift += realized_growth * 0.5
                    total_milkshake_lift += realized_growth * 0.5
                # Strategy 3: Milkshake focused
                elif j == 2:
                    total_milkshake_lift += realized_growth
            
            # Apply lifts
            new_coffee_pct = coffee_base * (1 + total_coffee_lift)
            new_milkshake_pct = milkshake_base * (1 + total_milkshake_lift)
            
            projections[month] = {
                'coffee_pct': new_coffee_pct,
                'coffee_growth': f"+{total_coffee_lift * 100:.1f}%",
                'coffee_revenue': current['coffee_revenue'] * (1 + total_coffee_lift),
                'milkshake_pct': new_milkshake_pct,
                'milkshake_growth': f"+{total_milkshake_lift * 100:.1f}%",
                'milkshake_revenue': current['milkshake_revenue'] * (1 + total_milkshake_lift),
                'combined_pct': new_coffee_pct + new_milkshake_pct,
                'combined_lift': f"+{((new_coffee_pct + new_milkshake_pct) / (coffee_base + milkshake_base) - 1) * 100:.1f}%"
            }
        
        self.insights['projections'] = projections
        
        print("\n" + "=" * 70)
        print("12-MONTH REVENUE PROJECTION (DATA-BACKED)")
        print("=" * 70)
        print(f"\nBase Revenue: Coffee={current['coffee_revenue']:,.0f}, "
              f"Milkshake={current['milkshake_revenue']:,.0f}")
        
        for period, data in projections.items():
            print(f"\n{period.upper().replace('_', ' ')}:")
            print(f"  Coffee: {data['coffee_pct']:.2f}% of total", end="")
            if 'coffee_revenue' in data:
                print(f" (Revenue: {data['coffee_revenue']:,.0f}, {data['coffee_growth']})", end="")
            print()
            
            print(f"  Milkshake: {data['milkshake_pct']:.2f}% of total", end="")
            if 'milkshake_revenue' in data:
                print(f" (Revenue: {data['milkshake_revenue']:,.0f}, {data['milkshake_growth']})", end="")
            print()
            
            print(f"  Combined: {data['combined_pct']:.2f}%", end="")
            if 'combined_lift' in data:
                print(f" ({data['combined_lift']} overall)", end="")
            print()
        
        return projections

# ============================================================================
# STEP 2: API ENDPOINT (DYNAMIC - Uses Real Analysis Results)
# ============================================================================

def growth_recommendations_endpoint(analysis_insights, category='all'):
    """
    FastAPI Endpoint Implementation - WITH REAL DATA
    
    Args:
        analysis_insights: Dictionary from CoffeeAndMilkshakeAnalysis.insights
        category: 'coffee' | 'milkshake' | 'all'
    
    Returns:
        JSON with dynamic recommendations based on actual analysis
    """
    
    # Extract data from analysis
    current = analysis_insights.get('current_state', {})
    opportunities = analysis_insights.get('opportunities', [])
    projections = analysis_insights.get('projections', {})
    segments = analysis_insights.get('segments', {})
    
    # Build dynamic response
    response = {
        "status": "success",
        "objective": "Coffee and Milkshake Growth Strategy",
        "analysis_date": datetime.now().isoformat(),
        "data_source": "REAL DATA from rep_s_00191_SMRY.csv and rep_s_00150.csv",
        
        # REAL: Current state from actual analysis
        "current_state": {
            "coffee_pct": round(current.get('coffee_pct_of_total', 0), 2),
            "coffee_revenue": round(current.get('coffee_revenue', 0), 2),
            "coffee_status": current.get('coffee_status', 'UNKNOWN'),
            "milkshake_pct": round(current.get('milkshake_pct_of_total', 0), 2),
            "milkshake_revenue": round(current.get('milkshake_revenue', 0), 2),
            "milkshake_status": current.get('milkshake_status', 'UNKNOWN'),
            "combined_pct": round(current.get('combined_pct', 0), 2),
            "total_revenue": round(current.get('total_revenue', 0), 2),
            "top_coffee_products": [
                {
                    "product": p.get("product", ""),
                    "revenue": round(p.get("amount", 0), 2),
                    "qty": round(p.get("qty", 0), 2)
                }
                for p in current.get('top_coffee_products', [])[:3]
            ],
            "top_milkshake_products": [
                {
                    "product": p.get("product", ""),
                    "revenue": round(p.get("amount", 0), 2),
                    "qty": round(p.get("qty", 0), 2)
                }
                for p in current.get('top_milkshake_products', [])[:3]
            ]
        },
        
        # REAL: Customer segments from actual data
        "customer_segments": {
            name: {
                "count": seg.get("count", 0),
                "percentage": round(seg.get("pct_of_customers", 0), 1),
                "avg_lifetime_value": round(seg.get("avg_order_value", 0), 2),
                "description": seg.get("description", "")
            }
            for name, seg in segments.items()
        },
        
        # REAL: Strategies from actual analysis
        "strategies": [
            {
                "rank": opp['id'],
                "name": opp['name'],
                "growth": opp['growth_potential'],
                "data_insight": opp.get('data_insight', ''),
                "timeline": opp['timeline'],
                "cost": opp['cost'],
                "priority": "IMMEDIATE" if opp['timeline'].startswith('1 ') or opp['timeline'].startswith('2 ') else "PLAN_NOW",
                "implementation": opp['implementation'],
                "target_segment": opp['target_segment']
            }
            for opp in opportunities
        ],
        
        # REAL: Projections from actual analysis
        "projections": {
            "month_1": {
                "coffee_pct": round(projections.get('month_1', {}).get('coffee_pct', 0), 2),
                "milkshake_pct": round(projections.get('month_1', {}).get('milkshake_pct', 0), 2),
                "combined_lift": projections.get('month_1', {}).get('combined_lift', '+0%')
            },
            "month_3": {
                "coffee_pct": round(projections.get('month_3', {}).get('coffee_pct', 0), 2),
                "milkshake_pct": round(projections.get('month_3', {}).get('milkshake_pct', 0), 2),
                "combined_lift": projections.get('month_3', {}).get('combined_lift', '+0%')
            },
            "month_6": {
                "coffee_pct": round(projections.get('month_6', {}).get('coffee_pct', 0), 2),
                "milkshake_pct": round(projections.get('month_6', {}).get('milkshake_pct', 0), 2),
                "combined_lift": projections.get('month_6', {}).get('combined_lift', '+0%')
            },
            "month_12": {
                "coffee_pct": round(projections.get('month_12', {}).get('coffee_pct', 0), 2),
                "milkshake_pct": round(projections.get('month_12', {}).get('milkshake_pct', 0), 2),
                "combined_lift": projections.get('month_12', {}).get('combined_lift', '+0%')
            }
        },
        
        # Determine recommended action based on analysis
        "recommended_action": f"LAUNCH {opportunities[0]['name']} immediately" 
                             if opportunities else "Conduct analysis first",
        
        "next_actions": [
            {
                "action": f"Launch {opp['name']}",
                "owner": "Operations Team",
                "deadline": opp['timeline'],
                "expected_lift": opp['growth_potential']
            }
            for opp in opportunities
        ],
        
        "target_metrics": {
            "revenue_lift_12_months": projections.get('month_12', {}).get('combined_lift', '+0%'),
            "customer_segment_focus": [name.replace('_', ' ').title() for name in segments.keys()],
            "estimated_roi": "200-350% (year 1) based on customer retention and upsell"
        }
    }
    
    return response

# ============================================================================
# STEP 3: EXECUTION EXAMPLE
# ============================================================================

def main():
    """
    Run complete analysis with REAL DATA
    
    Output:
      1. Console output with insights
      2. Saved insights to JSON
      3. API response ready for dashboard
    """
    
    print("\n" + "=" * 70)
    print("OBJECTIVE 5: COFFEE & MILKSHAKE GROWTH STRATEGY")
    print("=" * 70)
    print("Loading REAL data from CSV files...\n")
    
    # Load REAL data from CSV files
    try:
        products_df = load_products_by_division('rep_s_00191_SMRY.csv')
        customers_df = load_customers('rep_s_00150.csv')
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("Please ensure CSV files are in the current directory.")
        return None
    
    # Run analysis with REAL data
    analysis = CoffeeAndMilkshakeAnalysis(products_df, customers_df)
    
    # Execute each analysis step
    analysis.current_state_analysis()
    analysis.customer_segment_analysis()
    analysis.growth_opportunity_analysis()
    analysis.revenue_projection()
    
    # Generate API response WITH REAL DATA from analysis
    print("\n" + "=" * 70)
    print("API RESPONSE (will be returned from /api/growth-recommendations)")
    print("=" * 70)
    
    api_response = growth_recommendations_endpoint(analysis.insights)
    print(json.dumps(api_response, indent=2))
    
    # Save findings
    import os
    os.makedirs('./objectives_output', exist_ok=True)
    with open('./objectives_output/05_objective_growth_insights.json', 'w') as f:
        json.dump(api_response, f, indent=2)
    
    print("\nAnalysis complete. Results saved to objectives_output/")
    print("=" * 70)
    
    # Summary
    current = analysis.insights['current_state']
    projections = analysis.insights['projections']
    
    print("\nEXECUTIVE SUMMARY:")
    print(f"  - Current State: Coffee={current['coffee_pct_of_total']:.1f}%, Milkshake={current['milkshake_pct_of_total']:.1f}%")
    print(f"  - Coffee Revenue: {current.get('coffee_revenue', 0):,.0f} LBP (${current.get('coffee_revenue', 0)/89500:,.0f} USD)")
    print(f"  - Milkshake Revenue: {current.get('milkshake_revenue', 0):,.0f} LBP (${current.get('milkshake_revenue', 0)/89500:,.0f} USD)")
    print(f"  - Total Revenue: {current.get('total_revenue', 0):,.0f} LBP (${current.get('total_revenue', 0)/89500:,.0f} USD)")
    print(f"  - Currency: LBP (Lebanese Pound), Conversion: 1 USD = 89,500 LBP")
    print(f"  - 12-Month Projection: {projections['month_12']['combined_lift']}")
    print(f"  - Top Recommendation: {analysis.insights['opportunities'][0]['name']}")
    print(f"  - Customer Segments Identified: {len(analysis.insights['segments'])}")
    print("\n")
    
    return analysis.insights

if __name__ == '__main__':
    insights = main()


