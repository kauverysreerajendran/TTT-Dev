#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

from Jig_Loading.models import JigCompleted
from modelmasterapp.models import TotalStockModel, ModelMasterCreation

# Find the record from the screenshot
jig = JigCompleted.objects.filter(jig_id='J144-0002').first()
if jig:
    print(f"✅ Found JigCompleted: {jig.jig_id}")
    print(f"   lot_id: {jig.lot_id}")
    print(f"   draft_data keys: {jig.draft_data.keys() if jig.draft_data else 'None'}")
    
    # Check TotalStockModel for plating color
    tsm = TotalStockModel.objects.filter(lot_id=jig.lot_id).first()
    if tsm:
        print(f"\n✅ Found TotalStockModel: {tsm.lot_id}")
        print(f"   batch_id: {tsm.batch_id}")
        print(f"   batch_id.id: {tsm.batch_id.id if tsm.batch_id else 'None'}")
        print(f"   plating_color: {tsm.plating_color}")
        if tsm.plating_color:
            print(f"   plating_color.plating_color: {tsm.plating_color.plating_color}")
        
        # Check the ModelMasterCreation record
        if tsm.batch_id:
            print(f"\n   Checking ModelMasterCreation (batch_id object={tsm.batch_id}):")
            print(f"   ✅ ModelMasterCreation object is: {tsm.batch_id}")
            print(f"      plating_stk_no: {tsm.batch_id.plating_stk_no}")
            print(f"      plating_color (field): {tsm.batch_id.plating_color}")
            print(f"      model_stock_no: {tsm.batch_id.model_stock_no}")
    else:
        print(f"\n❌ No TotalStockModel found for lot_id: {jig.lot_id}")
else:
    print("❌ JigCompleted with jig_id='J144-0002' not found")
    # List some available records
    jigs = JigCompleted.objects.all()[:5]
    print(f"\nAvailable JigCompleted records (first 5):")
    for j in jigs:
        print(f"  - {j.jig_id} (lot_id: {j.lot_id})")

