#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

from JigUnloading_Zone2.views import JU_Zone_MainTable
from django.test import RequestFactory

def test_template_data():
    print("Testing Jig Unloading Zone 2 Template Data...")

    factory = RequestFactory()
    request = factory.get('/jig-unloading-zone2/')
    view = JU_Zone_MainTable()
    view.request = request

    try:
        context = view.get_context_data()
        print("✅ SUCCESS: get_context_data() executed without errors")

        jig_unload = context.get('jig_unload')
        if jig_unload:
            print(f"   Found {len(jig_unload)} jig records")
            if hasattr(jig_unload, 'object_list'):
                first_jig = jig_unload.object_list[0]
            else:
                first_jig = jig_unload[0]

            print(f"   First jig lot_id: {getattr(first_jig, 'lot_id', 'N/A')}")
            print(f"   final_version_names: {getattr(first_jig, 'final_version_names', 'N/A')}")
            print(f"   final_polishing_stk_nos: {getattr(first_jig, 'final_polishing_stk_nos', 'N/A')}")
            print(f"   total_quantity: {getattr(first_jig, 'total_quantity', 'N/A')}")

            # Check all three records
            all_jigs = jig_unload.object_list if hasattr(jig_unload, 'object_list') else jig_unload
            for i, jig in enumerate(all_jigs[:3]):  # Check first 3
                print(f"   Jig {i+1}: {jig.lot_id}")
                print(f"     - Model Presents: {getattr(jig, 'final_version_names', 'N/A')}")
                print(f"     - Polishing Stk No: {getattr(jig, 'final_polishing_stk_nos', 'N/A')}")
                print(f"     - Lot Qty: {getattr(jig, 'total_quantity', 'N/A')}")
        else:
            print("   ❌ No jig_unload data found in context")

    except Exception as e:
        print(f"❌ ERROR in get_context_data(): {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_template_data()