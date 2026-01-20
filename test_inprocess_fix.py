#!/usr/bin/env python3
"""
Test script to validate the Inprocess Inspection modal fix
"""
import os
import sys
import django
from django.conf import settings

# Add the project directory to the Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.append(project_dir)

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

# Now import Django models and views
from Inprocess_Inspection.views import InprocessInspectionView
from Jig_Loading.models import JigCompleted
from modelmasterapp.models import ModelMaster
from django.test import RequestFactory
from django.contrib.auth.models import User

def test_inprocess_inspection_modal_fix():
    """Test the modal fix for Inprocess Inspection"""
    print("🔍 Testing Inprocess Inspection Modal Fix")
    print("=" * 50)
    
    try:
        # Create a mock request
        factory = RequestFactory()
        request = factory.get('/inprocess_inspection/inprocess_inspection_main/')
        
        # Create a view instance
        view = InprocessInspectionView()
        view.request = request
        
        # Get context data
        print("📋 Fetching context data...")
        context = view.get_context_data()
        
        # Check jig_details
        jig_details = context.get('jig_details', [])
        print(f"📊 Found {len(jig_details)} jig details")
        
        # Check each jig detail for model data
        for idx, jig_detail in enumerate(jig_details):
            print(f"\n🔧 JIG DETAIL #{idx + 1}:")
            print(f"   ID: {getattr(jig_detail, 'id', 'N/A')}")
            print(f"   Lot ID: {getattr(jig_detail, 'lot_id', 'N/A')}")
            print(f"   final_plating_stk_nos: {getattr(jig_detail, 'final_plating_stk_nos', 'N/A')}")
            print(f"   no_of_model_cases: {getattr(jig_detail, 'no_of_model_cases', 'N/A')}")
            print(f"   model_colors: {getattr(jig_detail, 'model_colors', 'N/A')}")
            print(f"   model_images keys: {list(getattr(jig_detail, 'model_images', {}).keys())}")
            
            # Validate the fix
            has_models = bool(getattr(jig_detail, 'no_of_model_cases', []))
            has_colors = bool(getattr(jig_detail, 'model_colors', {}))
            has_images = bool(getattr(jig_detail, 'model_images', {}))
            
            print(f"   ✅ Fix validation:")
            print(f"      Has models: {has_models}")
            print(f"      Has colors: {has_colors}")
            print(f"      Has images: {has_images}")
            
            if has_models and has_colors and has_images:
                print(f"   🎉 FIX SUCCESSFUL for JigDetail #{idx + 1}")
            else:
                print(f"   ❌ FIX INCOMPLETE for JigDetail #{idx + 1}")
        
        print(f"\n📈 SUMMARY:")
        successful_fixes = sum(1 for jig in jig_details if 
                              bool(getattr(jig, 'no_of_model_cases', [])) and 
                              bool(getattr(jig, 'model_colors', {})) and 
                              bool(getattr(jig, 'model_images', {})))
        
        print(f"   Total jigs: {len(jig_details)}")
        print(f"   Successfully fixed: {successful_fixes}")
        print(f"   Success rate: {(successful_fixes/len(jig_details)*100):.1f}%" if jig_details else "N/A")
        
        if successful_fixes == len(jig_details) and len(jig_details) > 0:
            print("   🎉 ALL FIXES SUCCESSFUL!")
            return True
        else:
            print("   ⚠️ Some fixes incomplete")
            return False
            
    except Exception as e:
        print(f"❌ Error testing fix: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_inprocess_inspection_modal_fix()
    sys.exit(0 if success else 1)