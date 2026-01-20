#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

from Inprocess_Inspection.views import InprocessInspectionView
from Jig_Loading.models import JigCompleted
from modelmasterapp.models import TotalStockModel

# Test the extract_model_data method
view = InprocessInspectionView()

# Find the record
jig = JigCompleted.objects.filter(jig_id='J144-0002').first()
if jig:
    print(f"✅ Found JigCompleted: {jig.jig_id}")
    print(f"   lot_id: {jig.lot_id}")
    
    # Get the TotalStockModel
    tsm = TotalStockModel.objects.filter(lot_id=jig.lot_id).first()
    if tsm and tsm.batch_id:
        print(f"\n✅ Testing extract_model_data with ModelMasterCreation ID={tsm.batch_id.id}")
        
        # Test the extract_model_data method
        model_data = view.extract_model_data(tsm.batch_id, 'ModelMasterCreation')
        
        print(f"\nExtracted Model Data:")
        print(f"   model_no: {model_data['model_no']}")
        print(f"   plating_color: {model_data['plating_color']}")
        print(f"   plating_stk_no: {model_data['plating_stk_no']}")
        print(f"   tray_type: {model_data['tray_type']}")
        print(f"   tray_capacity: {model_data['tray_capacity']}")
        
        # Check if the values are correct
        if model_data['plating_color'] == 'BLACK':
            print(f"\n✅ PASS: Plating Color correctly fetched from TotalStockModel!")
        else:
            print(f"\n❌ FAIL: Expected 'BLACK', got '{model_data['plating_color']}'")
            
else:
    print("❌ JigCompleted with jig_id='J144-0002' not found")
