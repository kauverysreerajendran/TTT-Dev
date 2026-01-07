#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

# Test the web view
from django.test import RequestFactory
from Jig_Loading.views import JigAddModalDataView

try:
    print("=== TESTING WEB VIEW ===")
    
    factory = RequestFactory()
    request = factory.get('/jig_loading/jig-add-modal-data/?batch_id=BATCH-20260103222521-43&lot_id=LID040120260015240001&jig_qr_id=&broken_hooks=39')
    
    view = JigAddModalDataView()
    response = view.get(request)
    
    print(f"Response status: {response.status_code}")
    if hasattr(response, 'content'):
        import json
        data = json.loads(response.content)
        print(f"effective_loaded_cases: {data.get('effective_loaded_cases')}")
        print(f"broken_buildup_hooks: {data.get('broken_buildup_hooks')}")
        print(f"delink_table count: {len(data.get('delink_table', []))}")
        
        # Print delink table
        delink_table = data.get('delink_table', [])
        print("\\nDelink table:")
        for i, tray in enumerate(delink_table):
            print(f"  {i+1}: {tray.get('tray_id')} - {tray.get('tray_quantity')} cases")
    
    print("\\n✅ Web view test completed successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()