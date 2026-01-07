#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

# Now test the functionality
from modelmasterapp.models import TotalStockModel, ModelMasterCreation
from Jig_Loading.models import JigLoadTrayId

try:
    print("=== TESTING BROKEN HOOKS LOGIC ===")
    
    # Get real data
    lot_id = 'LID040120260015240001'
    batch_id = 'BATCH-20260103222521-43'
    broken_hooks = 39
    
    lot = TotalStockModel.objects.get(lot_id=lot_id)
    batch = lot.batch_id
    
    print(f"Lot ID: {lot_id}")
    print(f"Batch ID: {batch_id}")
    print(f"Total Stock: {lot.total_stock}")
    print(f"Broken Hooks: {broken_hooks}")
    print(f"Effective Qty: {lot.total_stock - broken_hooks}")
    
    # Test the view logic manually
    from Jig_Loading.views import JigAddModalDataView
    view = JigAddModalDataView()
    
    # Test broken hooks calculation
    effective_qty = lot.total_stock - broken_hooks
    effective_trays = view._calculate_broken_hooks_tray_distribution(lot_id, effective_qty, broken_hooks)
    
    print(f"\\nEffective tray distribution: {len(effective_trays)} trays")
    for tray_data in effective_trays:
        print(f"  - {tray_data['tray_id']}: effective={tray_data['effective_qty']}, excluded={tray_data['excluded_qty']}")
    
    print("\\n✅ Test completed successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()