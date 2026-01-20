#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

from Jig_Loading.models import JigCompleted
from modelmasterapp.models import TotalStockModel
import json

# Find the record
jig = JigCompleted.objects.filter(jig_id='J144-0002').first()
if jig:
    print(f"✅ Found JigCompleted: {jig.jig_id}")
    print(f"   lot_id: {jig.lot_id}")
    
    # Check draft_data for tray info
    draft_data = jig.draft_data or {}
    print(f"\n   draft_data (for tray info):")
    print(f"      tray_type: {draft_data.get('tray_type', 'No Tray Type')}")
    print(f"      tray_capacity: {draft_data.get('tray_capacity', 0)}")
    
    # Check TotalStockModel for plating color
    tsm = TotalStockModel.objects.filter(lot_id=jig.lot_id).first()
    if tsm and tsm.plating_color:
        print(f"\n   From TotalStockModel:")
        print(f"      plating_color: {tsm.plating_color.plating_color}")
    
    # Check no_of_model_cases (Model Presents)
    no_of_model_cases = jig.no_of_model_cases
    print(f"\n   no_of_model_cases (Model Presents): {no_of_model_cases}")
    
    print(f"\n✅ Summary of what Inprocess Inspection should show:")
    print(f"   Model Presents: {no_of_model_cases if no_of_model_cases else 'Empty/Not Set'}")
    print(f"   Plating Color: {tsm.plating_color.plating_color if tsm and tsm.plating_color else 'No Plating Color'}")
    print(f"   Tray Type: {draft_data.get('tray_type', 'No Tray Type')}")
    print(f"   Tray Capacity: {draft_data.get('tray_capacity', 0)}")
    
else:
    print("❌ JigCompleted with jig_id='J144-0002' not found")
