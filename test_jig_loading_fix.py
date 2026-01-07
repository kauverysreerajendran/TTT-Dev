#!/usr/bin/env python
"""
Test script to verify the jig loading lot splitting fix
Expected results:
- Main lot: 63 cases, 7 trays (5 scanned + 2 automatic)
- Broken lot: 35 cases, 3 trays (1 half-filled + 2 automatic)
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import RequestFactory
from django.http import JsonResponse
from Jig_Loading.views import JigSaveAPIView
from Jig_Loading.models import JigDetails, JigLoadTrayId
from modelmasterapp.models import TotalStockModel
import json

def test_jig_loading_split():
    """Test the jig loading lot splitting functionality"""
    
    # Clean up any existing test data
    JigDetails.objects.filter(jig_qr_id__contains='TEST-JIG').delete()
    JigLoadTrayId.objects.filter(tray_id__contains='TEST').delete()
    TotalStockModel.objects.filter(lot_id__contains='TEST').delete()
    
    print("=== Testing Jig Loading Lot Splitting ===")
    print("Expected: Main lot 63 cases (7 trays), Broken lot 35 cases (3 trays)")
    print()
    
    # Create test data
    factory = RequestFactory()
    user = User.objects.first() or User.objects.create_user('testuser', 'test@test.com', 'pass123')
    
    # Test data matching the user's scenario
    test_data = {
        'jig_qr_id': 'TEST-JIG-001',
        'batch_id': 'testbatch001',
        'lot_id': 'TESTLOT001',
        'all_valid_trays': [
            {'tray_id': 'JA-A00155', 'tray_qty': '12'},  # Full tray
            {'tray_id': 'JA-A00156', 'tray_qty': '12'},  # Full tray  
            {'tray_id': 'JA-A00157', 'tray_qty': '12'},  # Full tray
            {'tray_id': 'JA-A00158', 'tray_qty': '12'},  # Full tray
            {'tray_id': 'JA-A00159', 'tray_qty': '2'},   # Partial tray (50 total scanned)
        ],
        'draft_data': {
            'broken_buildup_hooks': '35',  # 35 broken hooks
            'no_of_cycle': '1',
            'plating_stk_no': 'TEST-STK-001'
        },
        'half_filled_tray_data': [
            {'tray_id': 'JB-A00130', 'tray_qty': '11', 'row_index': 'half_0'}
        ],
        'ep_bath_type': 'Bright',
        'plating_color': 'Gold'
    }
    
    # Create a test TotalStockModel (original 98 cases)
    from modelmasterapp.models import ModelMasterCreation
    try:
        batch_obj = ModelMasterCreation.objects.get(batch_id='testbatch001')
    except ModelMasterCreation.DoesNotExist:
        print("Note: Test batch not found, creating mock data...")
        # This test would need actual batch data to run fully
        return False
    
    request = factory.post('/jig_loading/save/', json.dumps(test_data), content_type='application/json')
    request.user = user
    
    view = JigSaveAPIView()
    
    try:
        response = view.post(request)
        response_data = json.loads(response.content)
        
        if response_data.get('success'):
            print("✅ Jig save API call successful")
            
            # Check main lot results
            main_jig = JigDetails.objects.get(jig_qr_id='TEST-JIG-001')
            main_trays = JigLoadTrayId.objects.filter(lot_id='TESTLOT001')
            
            print(f"Main lot cases loaded: {main_jig.total_cases_loaded}")
            print(f"Main lot tray count: {main_trays.count()}")
            print(f"Main lot half_filled_tray_data: {main_jig.half_filled_tray_data}")
            
            # Check broken lot results
            broken_jigs = JigDetails.objects.filter(jig_qr_id__contains='TEST-JIG-001-BROKEN')
            if broken_jigs.exists():
                broken_jig = broken_jigs.first()
                broken_trays = JigLoadTrayId.objects.filter(lot_id=broken_jig.lot_id)
                
                print(f"Broken lot cases loaded: {broken_jig.total_cases_loaded}")
                print(f"Broken lot tray count: {broken_trays.count()}")
                print(f"Broken lot half_filled_tray_data: {broken_jig.half_filled_tray_data}")
                
                # Verify expected results
                main_lot_correct = (main_jig.total_cases_loaded == 63 and main_trays.count() == 7)
                broken_lot_correct = (broken_jig.total_cases_loaded == 35 and broken_trays.count() == 3)
                
                if main_lot_correct and broken_lot_correct:
                    print("✅ All test cases PASSED!")
                    return True
                else:
                    print("❌ Test cases FAILED - quantities or tray counts incorrect")
                    return False
            else:
                print("❌ Broken lot not created")
                return False
                
        else:
            print(f"❌ API call failed: {response_data.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

if __name__ == '__main__':
    test_jig_loading_split()