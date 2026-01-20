#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

from JigUnloading_Zone2.views import JU_Zone_MainTable
from django.test import RequestFactory

def test_ju_zone_main():
    print("Testing Jig Unloading Zone 2 Main Table View...")

    # Create a test request
    factory = RequestFactory()
    request = factory.get('/jig-unloading-zone2/')

    # Create the view instance
    view = JU_Zone_MainTable()
    view.request = request

    try:
        context = view.get_context_data()
        print("✅ SUCCESS: get_context_data() executed without errors")

        jig_unload = context.get('jig_unload')
        if jig_unload:
            print(f"   Found jig_unload data")
            if hasattr(jig_unload, 'object_list'):
                count = len(jig_unload.object_list)
                first_jig = jig_unload.object_list[0] if count > 0 else None
            else:
                count = len(jig_unload)
                first_jig = jig_unload[0] if count > 0 else None

            print(f"   Total jig records: {count}")

            if first_jig:
                print(f"   First jig lot_id: {getattr(first_jig, 'lot_id', 'N/A')}")
                print(f"   Has final_plating_stk_nos: {hasattr(first_jig, 'final_plating_stk_nos')}")
                print(f"   Has final_polishing_stk_nos: {hasattr(first_jig, 'final_polishing_stk_nos')}")
                print(f"   Has final_version_names: {hasattr(first_jig, 'final_version_names')}")

                # Check if the enhanced data is populated
                if hasattr(first_jig, 'final_plating_stk_nos'):
                    plating_data = getattr(first_jig, 'final_plating_stk_nos', [])
                    print(f"   final_plating_stk_nos: {plating_data}")

                if hasattr(first_jig, 'final_polishing_stk_nos'):
                    polishing_data = getattr(first_jig, 'final_polishing_stk_nos', [])
                    print(f"   final_polishing_stk_nos: {polishing_data}")

                if hasattr(first_jig, 'final_version_names'):
                    version_data = getattr(first_jig, 'final_version_names', [])
                    print(f"   final_version_names: {version_data}")
        else:
            print("   ❌ No jig_unload data found in context")

    except Exception as e:
        print(f"❌ ERROR in get_context_data(): {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ju_zone_main()