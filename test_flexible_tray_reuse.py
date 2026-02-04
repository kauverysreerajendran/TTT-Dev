"""
Test script for flexible tray reuse validation logic.
Tests the new Option C implementation with user-provided test data.
"""

def test_flexible_reuse_logic():
    """
    Test data from user:
    - 5 trays with qty [12, 12, 12, 12, 12]
    - Rejection qty: 25
    - Tray IDs: JB-A00101, JB-A00102, JB-A00103, JB-A00104, JB-A00105
    """
    
    tray_data = [
        {'id': 'JB-A00101', 'qty': 12, 'index': 0},
        {'id': 'JB-A00102', 'qty': 12, 'index': 1},
        {'id': 'JB-A00103', 'qty': 12, 'index': 2},
        {'id': 'JB-A00104', 'qty': 12, 'index': 3},
        {'id': 'JB-A00105', 'qty': 12, 'index': 4},
    ]
    
    rejection_qty = 25
    
    # Test scenarios from user's data
    test_scenarios = [
        {
            'name': 'Scenario 1: User selects JB-A00103 + JB-A00105 for 25 qty',
            'selected_trays': ['JB-A00103', 'JB-A00105'],
            'rejection_qty': 25,
            'expected': {
                'JB-A00103': 'ALLOWED',  # First selected, will consume 12 qty, leaving 13
                'JB-A00105': 'ALLOWED',  # Second selected, will consume 12 qty, leaving 1 (fully consumed!)
            }
        },
        {
            'name': 'Scenario 2: User selects JB-A00101 + JB-A00105 for 25 qty',
            'selected_trays': ['JB-A00101', 'JB-A00105'],
            'rejection_qty': 25,
            'expected': {
                'JB-A00101': 'ALLOWED',  # First selected, will consume 12 qty, leaving 13
                'JB-A00105': 'ALLOWED',  # Second selected, will consume 12 qty, leaving 1 (fully consumed!)
            }
        },
        {
            'name': 'Scenario 3: User selects JB-A00102 + JB-A00105 for 25 qty',
            'selected_trays': ['JB-A00102', 'JB-A00105'],
            'rejection_qty': 25,
            'expected': {
                'JB-A00102': 'ALLOWED',  # First selected, will consume 12 qty, leaving 13
                'JB-A00105': 'ALLOWED',  # Second selected, will consume 12 qty, leaving 1 (fully consumed!)
            }
        },
        {
            'name': 'Scenario 4: User selects JB-A00104 + JB-A00105 for 25 qty',
            'selected_trays': ['JB-A00104', 'JB-A00105'],
            'rejection_qty': 25,
            'expected': {
                'JB-A00104': 'ALLOWED',  # First selected, will consume 12 qty, leaving 13
                'JB-A00105': 'ALLOWED',  # Second selected, will consume 12 qty, leaving 1 (fully consumed!)
            }
        },
        {
            'name': 'Scenario 5: User tries JB-A00103 alone (no other trays selected)',
            'selected_trays': [],
            'rejection_qty': 25,
            'validating_tray': 'JB-A00103',
            'expected': {
                'JB-A00103': 'BLOCKED',  # Remaining qty is 25, but tray has only 12, won't fully consume
            }
        },
    ]
    
    print("=" * 80)
    print("FLEXIBLE TRAY REUSE VALIDATION - TEST RESULTS")
    print("=" * 80)
    print()
    
    for scenario in test_scenarios:
        print(f"📋 {scenario['name']}")
        print(f"   Selected trays: {scenario['selected_trays']}")
        print(f"   Rejection qty: {scenario['rejection_qty']}")
        print()
        
        # Calculate total already-selected qty
        already_selected_qty = 0
        for tray_id in scenario['selected_trays']:
            for tray in tray_data:
                if tray['id'] == tray_id:
                    already_selected_qty += tray['qty']
                    break
        
        remaining_rejection_qty = scenario['rejection_qty'] - already_selected_qty
        
        print(f"   Already-selected qty: {already_selected_qty}")
        print(f"   Remaining rejection qty: {remaining_rejection_qty}")
        print()
        
        # Now validate each tray that will be tested
        expected_results = scenario.get('expected', {})
        
        for tray_id, expected_status in expected_results.items():
            for tray in tray_data:
                if tray['id'] == tray_id:
                    current_tray_qty = tray['qty']
                    
                    # Check if tray will be completely consumed
                    will_be_consumed = (remaining_rejection_qty >= current_tray_qty) and (remaining_rejection_qty > 0)
                    
                    actual_status = 'ALLOWED' if will_be_consumed else 'BLOCKED'
                    
                    match = '✅' if actual_status == expected_status else '❌'
                    
                    print(f"   {match} {tray_id}:")
                    print(f"      - Current tray qty: {current_tray_qty}")
                    print(f"      - Remaining qty: {remaining_rejection_qty}")
                    print(f"      - Will be consumed? {remaining_rejection_qty >= current_tray_qty}")
                    print(f"      - Expected: {expected_status}, Got: {actual_status}")
                    print()
                    break
        
        print("-" * 80)
        print()
    
    print("\n" + "=" * 80)
    print("KEY INSIGHTS:")
    print("=" * 80)
    print()
    print("✅ FLEXIBLE TRAY SELECTION (Option C) LOGIC:")
    print("   1. User can select ANY tray (not just sequential)")
    print("   2. For each new tray validation:")
    print("      - Calculate already-selected qty for this rejection reason")
    print("      - Calculate remaining rejection qty")
    print("      - Check: Will this tray be completely consumed by remaining qty?")
    print("   3. If remaining_qty >= tray_qty → ALLOW (tray will be fully consumed)")
    print("   4. If remaining_qty < tray_qty → BLOCK (tray will have leftover)")
    print()
    print("📊 EXAMPLE WITH YOUR DATA:")
    print("   - Rejection qty: 25")
    print("   - User selects JB-A00104 (qty 12)")
    print("   - Remaining qty: 25 - 12 = 13")
    print("   - Now validating JB-A00105 (qty 12)")
    print("   - Is 13 >= 12? YES → ALLOW (will be fully consumed)")
    print()
    print("⚠️  IMPORTANT DIFFERENCE:")
    print("   OLD (Sequential): Only first 2 trays allowed (indices 0, 1)")
    print("   NEW (Flexible):   ANY tray allowed if remaining qty >= tray qty")
    print("=" * 80)

if __name__ == '__main__':
    test_flexible_reuse_logic()
