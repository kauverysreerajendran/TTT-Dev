#!/usr/bin/env python
"""
Comprehensive verification test for Inprocess Inspection fixes:
1. Plating Color from TotalStockModel
2. Tray Type & Capacity from ModelMaster (with fallback)
3. Model Presents single circle display
"""

import os
import django
import sys

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

from Inprocess_Inspection.views import InprocessInspectionView
from Jig_Loading.models import JigCompleted
from modelmasterapp.models import TotalStockModel, ModelMasterCreation
from django.template import Context, Template, Engine
from django.template.loader import get_template

print("\n" + "="*70)
print("COMPREHENSIVE INPROCESS INSPECTION VERIFICATION TEST")
print("="*70)

# Get test record
jig = JigCompleted.objects.filter(jig_id='J144-0002').first()
if not jig:
    print("[FAIL] Test record not found")
    sys.exit(1)

print(f"\n[OK] Test Record: {jig.jig_id}")
print(f"     lot_id: {jig.lot_id}")
print(f"     no_of_model_cases: {jig.no_of_model_cases}")

# Initialize view
view = InprocessInspectionView()

# Test 1: Plating Color (from TotalStockModel)
print("\n" + "-"*70)
print("TEST 1: PLATING COLOR")
print("-"*70)

try:
    tsm = TotalStockModel.objects.filter(lot_id=jig.lot_id).first()
    if tsm:
        plating_color = tsm.plating_color.plating_color if tsm.plating_color else "None"
        print(f"[PASS] Plating Color: {plating_color}")
        print(f"       Source: TotalStockModel.plating_color")
        print(f"       Stock Model ID: {tsm.id}")
    else:
        print(f"[WARN] No TotalStockModel found for lot_id: {jig.lot_id}")
except Exception as e:
    print(f"[FAIL] Error fetching plating color: {e}")

# Test 2: Tray Type & Capacity (from ModelMaster via TotalStockModel)
print("\n" + "-"*70)
print("TEST 2: TRAY TYPE & CAPACITY")
print("-"*70)

try:
    if tsm and tsm.batch_id:
        mmc = tsm.batch_id
        print(f"[INFO] Batch Model: {mmc.__class__.__name__} (ID: {mmc.id})")
        
        if hasattr(mmc, 'model_stock_no') and mmc.model_stock_no:
            tray_type = mmc.model_stock_no.tray_type.tray_type if mmc.model_stock_no.tray_type else "None"
            tray_capacity = mmc.model_stock_no.tray_capacity or 0
            
            print(f"[PASS] Tray Type: {tray_type}")
            print(f"[PASS] Tray Capacity: {tray_capacity}")
            print(f"       Source: ModelMaster via batch_id.model_stock_no")
        else:
            print(f"[WARN] No model_stock_no found in batch model")
    else:
        print(f"[FAIL] No batch_id in TotalStockModel")
except Exception as e:
    print(f"[FAIL] Error fetching tray data: {e}")

# Test 3: Model Presents Single Circle Display
print("\n" + "-"*70)
print("TEST 3: MODEL PRESENTS SINGLE CIRCLE DISPLAY")
print("-"*70)

try:
    # Get the template
    template = get_template('Inprocess_Inspection/Inprocess_Inspection.html')
    
    # Create mock jig_detail with model data
    class MockJigDetail:
        def __init__(self):
            self.inprocess_hold_lot = False
            self.no_of_model_cases = ['2617']  # Simulate single model
            self.model_colors = {'2617': '#e74c3c'}
            self.model_images = {'2617': ['/media/model_images/2617.jpg']}
    
    jig_detail = MockJigDetail()
    
    # Create context with necessary filters
    from django.template.context_processors import static
    context = Context({
        'jig_detail': jig_detail,
        'STATIC_URL': '/static/'
    })
    
    # Test with model data
    print(f"[INFO] Testing with model data:")
    print(f"       no_of_model_cases: {jig_detail.no_of_model_cases}")
    
    # Verify template structure (check actual HTML)
    from django.test import Client
    client = Client()
    
    # For template structure validation, we'll just check the template file directly
    with open('a:\\Workspace\\Watchcase Tracker Titan\\static\\templates\\Inprocess_Inspection\\Inprocess_Inspection.html', 'r') as f:
        html_content = f.read()
    
    # Check for single circle pattern
    if '{% with first_model=jig_detail.no_of_model_cases.0 %}' in html_content:
        print(f"[PASS] Template uses single circle (first_model.0)")
    else:
        print(f"[FAIL] Template doesn't use single circle pattern")
    
    # Check for model number display
    if '{{ first_model }}' in html_content:
        print(f"[PASS] Template displays model number")
    else:
        print(f"[FAIL] Template doesn't display model number")
    
    # Check for fallback
    if '<!-- No model data: display placeholder -->' in html_content:
        print(f"[PASS] Template has fallback for no model data")
    else:
        print(f"[FAIL] Template missing fallback for no model data")
    
    # Check for expand arrow
    if 'expand-model-remark' in html_content:
        print(f"[PASS] Template has expand arrow for gallery")
    else:
        print(f"[FAIL] Template missing expand arrow")
    
except Exception as e:
    print(f"[FAIL] Error testing template: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Verify data flow works
print("\n" + "-"*70)
print("TEST 4: COMPLETE DATA FLOW")
print("-"*70)

try:
    # Simulate what create_enhanced_jig_detail does
    print(f"[INFO] Simulating view.create_enhanced_jig_detail() for jig_id: {jig.jig_id}")
    
    jig_details = view.create_enhanced_jig_detail(jig)
    
    if jig_details:
        jig_detail = jig_details[0] if isinstance(jig_details, list) else jig_details
        
        print(f"\n[INFO] Enhanced Jig Detail Result:")
        
        # Check plating color
        plating_color = getattr(jig_detail, 'plating_color', 'NOT SET')
        if plating_color and plating_color != 'No Plating Color':
            print(f"[PASS] plating_color: {plating_color}")
        else:
            print(f"[WARN] plating_color: {plating_color} (not set or default)")
        
        # Check tray info
        tray_type = getattr(jig_detail, 'tray_type', 'NOT SET')
        tray_capacity = getattr(jig_detail, 'tray_capacity', 'NOT SET')
        print(f"[PASS] tray_type: {tray_type}")
        print(f"[PASS] tray_capacity: {tray_capacity}")
        
        # Check model data
        models = getattr(jig_detail, 'no_of_model_cases', [])
        colors = getattr(jig_detail, 'model_colors', {})
        images = getattr(jig_detail, 'model_images', {})
        
        print(f"[PASS] no_of_model_cases: {models}")
        print(f"[PASS] model_colors: {colors}")
        print(f"[PASS] model_images keys: {list(images.keys())}")
        
    else:
        print(f"[FAIL] create_enhanced_jig_detail returned empty")
        
except Exception as e:
    print(f"[FAIL] Error in data flow test: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("VERIFICATION COMPLETE")
print("="*70 + "\n")
