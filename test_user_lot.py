#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

from modelmasterapp.models import TotalStockModel
from Jig_Loading.models import JigLoadTrayId
from Jig_Loading.views import JigAddModalDataView

def test_user_specific_lot():
    print("=" * 60)
    print("🧪 TESTING USER'S SPECIFIC LOT")
    print("=" * 60)
    
    # User's data from the pick table
    lot_id = 'LID030120261910590039'  # 39 cases
    batch_id = 'BATCH-20260103222521-43'
    broken_hooks = 39
    
    # Check if this lot exists
    try:
        lot = TotalStockModel.objects.get(lot_id=lot_id)
        print(f"✅ Found lot: {lot.lot_id}")
        print(f"   Total Stock: {lot.total_stock}")
        print(f"   Batch ID: {lot.batch_id.batch_id if lot.batch_id else None}")
        
        # Get trays for this lot
        trays = JigLoadTrayId.objects.filter(lot_id=lot.lot_id)
        print(f"\\n📦 Original trays ({trays.count()}):")
        total_qty = 0
        for i, tray in enumerate(trays, 1):
            print(f"  {i}. {tray.tray_id:12s} - {tray.tray_quantity:2d} cases")
            total_qty += tray.tray_quantity
        print(f"Total tray qty: {total_qty}")
        
        # Now test broken hooks scenario
        # Since lot_qty=39 and broken_hooks=39, effective_qty would be 0
        # This doesn't make sense - you can't have broken hooks equal to lot qty
        
        print(f"\\n🔧 BROKEN HOOKS SCENARIO:")
        print(f"Original lot qty: {lot.total_stock}")
        print(f"Broken hooks: {broken_hooks}")
        effective_qty = lot.total_stock - broken_hooks
        print(f"Effective qty: {effective_qty}")
        
        if effective_qty <= 0:
            print("❌ ERROR: Effective quantity is 0 or negative!")
            print("   This means broken hooks >= lot quantity, which is invalid.")
            print("   Please check if you meant a different lot or different broken hooks value.")
        else:
            # Test the broken hooks calculation
            view = JigAddModalDataView()
            effective_trays = view._calculate_broken_hooks_tray_distribution(lot_id, effective_qty, broken_hooks)
            
            print(f"\\n🎯 EFFECTIVE TRAYS FOR DELINK ({len(effective_trays)} trays):")
            delink_total = 0
            for i, tray_data in enumerate(effective_trays, 1):
                delink_total += tray_data['effective_qty']
                print(f"  {i}. {tray_data['tray_id']:12s} - {tray_data['effective_qty']:2d} cases (excluded: {tray_data['excluded_qty']})")
            
            print(f"\\nDelink total: {delink_total} cases")
            print(f"Half-filled total: {lot.total_stock - delink_total} cases")
    
    except TotalStockModel.DoesNotExist:
        print(f"❌ Lot {lot_id} not found")

if __name__ == "__main__":
    test_user_specific_lot()