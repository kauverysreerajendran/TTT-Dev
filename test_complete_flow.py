#!/usr/bin/env python
import os
import django
import sys

# Set UTF-8 encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

from Inprocess_Inspection.views import InprocessInspectionView
from Jig_Loading.models import JigCompleted
from modelmasterapp.models import TotalStockModel
from django.test import RequestFactory

# Create a test request object
factory = RequestFactory()
request = factory.get('/inprocess_inspection_main/')

# Mock the user
from django.contrib.auth.models import AnonymousUser
request.user = AnonymousUser()

# Create the view instance
view = InprocessInspectionView()
view.request = request

# Find the record
jig = JigCompleted.objects.filter(jig_id='J144-0002').first()
if jig:
    print(f"[OK] Found JigCompleted: {jig.jig_id}")
    print(f"   lot_id: {jig.lot_id}")
    
    # Get the TotalStockModel to fetch plating color
    tsm = TotalStockModel.objects.filter(lot_id=jig.lot_id).first()
    
    # Test the Inprocess Inspection view's data enhancement
    # Get multiple_lot_ids
    multiple_lot_ids = view.get_multiple_lot_ids(jig)
    print(f"\n   multiple_lot_ids: {multiple_lot_ids}")
    
    # Get lot_ids_data
    lot_ids_data = view.process_new_lot_ids(multiple_lot_ids)
    
    # Get model_cases_data
    model_cases_data = view.process_model_cases_corrected(jig.no_of_model_cases, multiple_lot_ids)
    
    # Create enhanced jig_detail
    enhanced_jig_detail = view.create_enhanced_jig_detail(jig, lot_ids_data, model_cases_data)
    
    print(f"\n[OK] Enhanced JigDetail attributes (what Inprocess Inspection will display):")
    print(f"   model_presents: {enhanced_jig_detail.model_presents}")
    print(f"   plating_color: {enhanced_jig_detail.plating_color}")
    print(f"   tray_type: {enhanced_jig_detail.tray_type}")
    print(f"   tray_capacity: {enhanced_jig_detail.tray_capacity}")
    print(f"   no_of_model_cases: {enhanced_jig_detail.no_of_model_cases}")
    
    print(f"\n[OK] VERIFICATION:")
    
    # Check plating_color
    if enhanced_jig_detail.plating_color == 'BLACK':
        print(f"   [PASS] Plating Color: BLACK (correctly from TotalStockModel)")
    else:
        print(f"   [FAIL] Plating Color: {enhanced_jig_detail.plating_color}")
    
    # Check tray info (should now have fallback from model)
    if enhanced_jig_detail.tray_type and enhanced_jig_detail.tray_type != 'No Tray Type':
        print(f"   [PASS] Tray Type: {enhanced_jig_detail.tray_type} (from model data fallback)")
    else:
        print(f"   [FAIL] Tray Type: {enhanced_jig_detail.tray_type}")
    
    if enhanced_jig_detail.tray_capacity and enhanced_jig_detail.tray_capacity > 0:
        print(f"   [PASS] Tray Capacity: {enhanced_jig_detail.tray_capacity} (from model data fallback)")
    else:
        print(f"   [FAIL] Tray Capacity: {enhanced_jig_detail.tray_capacity}")

else:
    print("[FAIL] JigCompleted with jig_id='J144-0002' not found")

