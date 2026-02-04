"""
CLARIFICATION TEST: Understanding the exact allocation strategy
"""

print("""
SCENARIO ANALYSIS:
==================

Given: 5 trays [12, 12, 12, 12, 12] = 60 total qty
Rejection Qty: 25

YOUR DATA SHOWS:

- R01 with 25 qty can use ANY 2 trays:
  ✅ JB-A00103 + JB-A00105 (indices 2 + 4)
  ✅ JB-A00101 + JB-A00105 (indices 0 + 4)  
  ✅ JB-A00102 + JB-A00105 (indices 1 + 4)
  ✅ JB-A00104 + JB-A00105 (indices 3 + 4)

QUESTION: How should the 25 qty be distributed across selected trays?

OPTION A: EQUAL DISTRIBUTION
If user selects 2 trays → 25 / 2 = 12.5 each
Tray 1: 12 - 12.5 = -0.5 (OVER consumption - shouldn't allow)
Tray 2: 12 - 12.5 = -0.5 (OVER consumption - shouldn't allow)
Result: ❌ This doesn't work

OPTION B: SEQUENTIAL FROM SELECTED TRAYS
If user selects [JB-A00104, JB-A00105]:

- Consume from JB-A00104 first: min(25, 12) = 12 consumed, 13 remaining
- Consume from JB-A00105 next: min(13, 12) = 12 consumed, 1 remaining
- JB-A00104: 12 - 12 = 0 ✅ EMPTIED
- JB-A00105: 12 - 12 = 0 ✅ EMPTIED
  Result: ✅ Both selected trays are completely emptied

Validation: "Can I add JB-A00104?"

- This would be the FIRST selection
- Remaining qty: 25 - 0 = 25
- JB-A00104 qty: 12
- After consuming: 12 will be fully consumed (25 >= 12) ✅ ALLOW

Then validation: "Can I add JB-A00105?"

- This would be the SECOND selection
- Remaining qty: 25 - 12 = 13 (after previous tray)
- JB-A00105 qty: 12
- After consuming: 12 will be fully consumed (13 >= 12) ✅ ALLOW

OPTION B SEEMS CORRECT!

Key insight: The order of user selection matters for validation:

- First selected tray uses: rejection_qty - 0 = rejection_qty
- Second selected tray uses: rejection_qty - first_tray_qty
- Third selected tray uses: rejection_qty - first_tray_qty - second_tray_qty
- etc.

So the backend needs to know THE ORDER OF SELECTION in current_session_allocations!
""")
