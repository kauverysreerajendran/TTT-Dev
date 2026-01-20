#!/usr/bin/env python
"""
Test to verify Model Presents data is populated correctly
"""

import os
import django
import sys

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

from Jig_Loading.models import JigCompleted
from django.test import RequestFactory
from Inprocess_Inspection.views import InprocessInspectionView

print("\n" + "="*70)
print("MODEL PRESENTS DATA POPULATION TEST")
print("="*70)

# Get test record
jig = JigCompleted.objects.filter(jig_id='J144-0002').first()
if not jig:
    print("[FAIL] Test record not found")
    sys.exit(1)

print(f"\n[OK] Test Record: {jig.jig_id}")
print(f"     lot_id: {jig.lot_id}")
print(f"     Original no_of_model_cases: {jig.no_of_model_cases} (type: {type(jig.no_of_model_cases)})")

# Create view instance and request
factory = RequestFactory()
request = factory.get('/')
view = InprocessInspectionView()
view.request = request

print(f"\n[INFO] Testing parse_model_cases with original data...")
parsed = view.parse_model_cases(jig.no_of_model_cases)
print(f"[OK] Parsed result: {parsed} (type: {type(parsed)})")

# Now test the full processing
print(f"\n[INFO] Testing full jig_detail processing...")

# Get context
context = view.get_context_data()
jig_details_page = context.get('jig_details', None)

if jig_details_page:
    # Get the test record from paginated results
    found_test_record = False
    for jig_detail in jig_details_page:
        if jig_detail.jig_id == 'J144-0002':
            found_test_record = True
            print(f"\n[OK] Found J144-0002 in processed jig_details")
            
            # Check the critical fields
            print(f"\n[CHECK] no_of_model_cases: {jig_detail.no_of_model_cases}")
            print(f"[CHECK] model_colors: {getattr(jig_detail, 'model_colors', 'NOT SET')}")
            print(f"[CHECK] model_images: {getattr(jig_detail, 'model_images', 'NOT SET')}")
            
            # Verify data is not empty
            if jig_detail.no_of_model_cases:
                print(f"\n[PASS] no_of_model_cases is populated!")
                if hasattr(jig_detail, 'model_colors') and jig_detail.model_colors:
                    print(f"[PASS] model_colors is populated!")
                    print(f"       Colors: {jig_detail.model_colors}")
                else:
                    print(f"[WARN] model_colors is NOT populated")
                    print(f"       This will show as empty in gallery")
                
                if hasattr(jig_detail, 'model_images') and jig_detail.model_images:
                    print(f"[PASS] model_images is populated!")
                    print(f"       Images keys: {list(jig_detail.model_images.keys())}")
                else:
                    print(f"[WARN] model_images is NOT populated")
                    print(f"       This will show placeholder images in gallery")
            else:
                print(f"[FAIL] no_of_model_cases is EMPTY - data not being extracted!")
                print(f"       Original: {jig.no_of_model_cases}")
            
            break
    
    if not found_test_record:
        print(f"\n[FAIL] J144-0002 not found in processed jig_details")
else:
    print(f"\n[FAIL] Could not get jig_details from context")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70 + "\n")
