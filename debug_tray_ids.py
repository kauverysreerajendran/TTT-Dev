#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

from modelmasterapp.models import TotalStockModel
from Jig_Loading.models import JigLoadTrayId

def debug_tray_issue():
    print("=" * 60)
    print("🐛 DEBUGGING TRAY ID ISSUE")
    print("=" * 60)
    
    # Find all lots with tray data
    all_lots = TotalStockModel.objects.filter(Jig_Load_completed=False)[:10]
    
    for lot in all_lots:
        print(f"\\n📦 Lot ID: {lot.lot_id}")
        print(f"   Total Stock: {lot.total_stock}")
        print(f"   Batch ID: {lot.batch_id.batch_id if lot.batch_id else 'None'}")
        
        # Get trays for this lot
        trays = JigLoadTrayId.objects.filter(lot_id=lot.lot_id)
        if trays.exists():
            print(f"   Trays ({trays.count()}):")
            total_qty = 0
            for i, tray in enumerate(trays, 1):
                print(f"     {i}. {tray.tray_id} - {tray.tray_quantity} cases")
                total_qty += tray.tray_quantity
            print(f"   Total tray qty: {total_qty}")
        else:
            print(f"   No trays found")
        
        print("-" * 40)

if __name__ == "__main__":
    debug_tray_issue()