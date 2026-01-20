#!/usr/bin/env python
"""
Simple template structure validation test
"""

import os
import re

print("\n" + "="*70)
print("TEMPLATE STRUCTURE VALIDATION TEST")
print("="*70 + "\n")

# Read the HTML template
html_file = 'a:\\Workspace\\Watchcase Tracker Titan\\static\\templates\\Inprocess_Inspection\\Inprocess_Inspection.html'

with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
    html_content = f.read()

tests_passed = 0
tests_total = 0

# Test 1: Single circle pattern (using first_model.0)
tests_total += 1
if 'first_model=jig_detail.no_of_model_cases.0' in html_content:
    print("[PASS] Template uses single circle pattern (first_model=jig_detail.no_of_model_cases.0)")
    tests_passed += 1
else:
    print("[FAIL] Template doesn't use single circle pattern")

# Test 2: Model number display
tests_total += 1
if '{{ first_model }}' in html_content and 'font-size:11px' in html_content:
    print("[PASS] Template displays model number with styling (font-size:11px)")
    tests_passed += 1
else:
    print("[FAIL] Template doesn't display model number properly")

# Test 3: Color circle using get_item filter
tests_total += 1
if 'model-circle' in html_content and 'get_item:first_model' in html_content:
    print("[PASS] Template applies color to first_model circle (get_item:first_model)")
    tests_passed += 1
else:
    print("[FAIL] Template doesn't apply color to circle")

# Test 4: Fallback for no model data
tests_total += 1
if 'background:#ccc' in html_content and '>N/A<' in html_content:
    print("[PASS] Template has fallback display for no model data (gray circle + N/A)")
    tests_passed += 1
else:
    print("[FAIL] Template missing fallback for no model data")

# Test 5: Expand arrow for gallery
tests_total += 1
if 'expand-model-remark' in html_content and 'View model gallery' in html_content:
    print("[PASS] Template has expand arrow icon for gallery")
    tests_passed += 1
else:
    print("[FAIL] Template missing expand arrow")

# Test 6: SVG down arrow icon
tests_total += 1
if '<svg' in html_content and 'polygon points' in html_content:
    print("[PASS] Template has SVG down arrow icon for expand")
    tests_passed += 1
else:
    print("[FAIL] Template missing SVG arrow icon")

# Test 7: Data attributes for gallery
tests_total += 1
data_attrs = ["data-images", "data-model-colors", "data-model-list"]
if all(attr in html_content for attr in data_attrs):
    print("[PASS] Template has all data attributes for gallery (data-images, data-model-colors, data-model-list)")
    tests_passed += 1
else:
    print("[FAIL] Template missing data attributes")

# Test 8: No multiple model loop (should NOT have for loop on no_of_model_cases in Model Presents section)
tests_total += 1
# Extract Model Presents section
match = re.search(r'<!-- Model Presents.*?<!-- Plating Stock No', html_content, re.DOTALL)
if match:
    model_presents_section = match.group(0)
    # Check that there's NO "for model_no in jig_detail.no_of_model_cases" in this section
    if '{% for model_no in jig_detail.no_of_model_cases %}' not in model_presents_section:
        print("[PASS] Model Presents section does NOT have multiple model loop (uses single circle)")
        tests_passed += 1
    else:
        print("[FAIL] Model Presents section still has multiple model loop")
else:
    print("[WARN] Could not extract Model Presents section")

print("\n" + "-"*70)
print(f"RESULTS: {tests_passed}/{tests_total} tests passed")
print("-"*70 + "\n")

if tests_passed == tests_total:
    print("✅ ALL TEMPLATE STRUCTURE TESTS PASSED!")
    print("\nTemplate is correctly configured for:")
    print("  • Single color circle display")
    print("  • Model number reference text")
    print("  • Gray placeholder when no model data")
    print("  • Expand arrow for gallery")
    print("  • Data attributes for JavaScript handlers")
else:
    print(f"⚠️ {tests_total - tests_passed} test(s) failed")
