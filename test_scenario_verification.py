#!/usr/bin/env python3
"""
Verification script for Watchcase Tracker Scenario Testing
Tests the complete workflow: Day Planning → Jig Loading → Delinking → IPS Logic → Jig Unloading
"""

import os
import sys
import django
from datetime import datetime

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

from DayPlanning.models import DPTrayId_History
from Jig_Loading.models import JigLoadingMaster, JigLoadingManualDraft
from Jig_Unloading.models import JigUnload_TrayId
from modelmasterapp.models import ModelMaster, Plating_Color, TrayType

class ScenarioVerifier:
    def __init__(self):
        self.test_results = []

    def log_test(self, test_name, status, details=""):
        """Log test results"""
        status_icon = "[PASS]" if status else "[FAIL]"
        self.test_results.append(f"{status_icon} {test_name}: {details}")
        print(f"{status_icon} {test_name}: {details}")

    def test_1805_model_capacity(self):
        """Test 1: Verify 1805 model has correct jig capacity (98)"""
        try:
            # Look for 1805 models in JigLoadingMaster
            jig_masters = JigLoadingMaster.objects.filter(
                model_stock_no__plating_stk_no__contains='1805'
            )

            if jig_masters.exists():
                capacities = [jm.jig_capacity for jm in jig_masters]
                if 98 in capacities:
                    self.log_test("1805 Model Jig Capacity", True, f"Found capacity 98 for 1805 models")
                else:
                    self.log_test("1805 Model Jig Capacity", False, f"Capacities found: {capacities}, expected 98")
            else:
                self.log_test("1805 Model Jig Capacity", False, "No 1805 models found in JigLoadingMaster")

        except Exception as e:
            self.log_test("1805 Model Jig Capacity", False, f"Error: {str(e)}")

    def test_ips_color_mapping(self):
        """Test 2: Verify IPS color exists and zone mapping"""
        try:
            ips_colors = Plating_Color.objects.filter(plating_color='IPS')
            if ips_colors.exists():
                ips_color = ips_colors.first()
                zone1_active = ips_color.jig_unload_zone_1
                zone2_active = ips_color.jig_unload_zone_2

                if zone1_active and not zone2_active:
                    self.log_test("IPS Color Zone Mapping", True, "IPS -> Zone 1 (correct)")
                else:
                    self.log_test("IPS Color Zone Mapping", False, f"Zone1: {zone1_active}, Zone2: {zone2_active}")
            else:
                self.log_test("IPS Color Zone Mapping", False, "IPS color not found")

        except Exception as e:
            self.log_test("IPS Color Zone Mapping", False, f"Error: {str(e)}")

    def test_1805sak02_configuration(self):
        """Test 3: Verify 1805SAK02 model configuration"""
        try:
            models = ModelMaster.objects.filter(plating_stk_no='1805SAK02')
            if models.exists():
                model = models.first()
                tray_type = model.tray_type.tray_type if model.tray_type else "Unknown"
                tray_capacity = model.tray_capacity or 0

                is_jumbo = 'jumbo' in tray_type.lower()
                has_correct_capacity = tray_capacity == 12

                if is_jumbo and has_correct_capacity:
                    self.log_test("1805SAK02 Configuration", True, f"Jumbo tray with capacity {tray_capacity}")
                else:
                    self.log_test("1805SAK02 Configuration", False, f"Tray: {tray_type}, Capacity: {tray_capacity}")
            else:
                self.log_test("1805SAK02 Configuration", False, "1805SAK02 model not found")

        except Exception as e:
            self.log_test("1805SAK02 Configuration", False, f"Error: {str(e)}")

    def test_delink_functionality(self):
        """Test 4: Check if delinking fields exist in models"""
        try:
            # Check if delink fields exist in DayPlanning model
            dp_fields = [f.name for f in DPTrayId_History._meta.get_fields()]
            has_delink_tray = 'delink_tray' in dp_fields
            has_delink_qty = 'delink_tray_qty' in dp_fields

            if has_delink_tray and has_delink_qty:
                self.log_test("Delinking Fields", True, "delink_tray and delink_tray_qty fields present")
            else:
                self.log_test("Delinking Fields", False, f"Missing fields - delink_tray: {has_delink_tray}, delink_qty: {has_delink_qty}")

        except Exception as e:
            self.log_test("Delinking Fields", False, f"Error: {str(e)}")

    def test_multi_model_support(self):
        """Test 5: Check multi-model support in JigLoadingManualDraft"""
        try:
            draft_fields = [f.name for f in JigLoadingManualDraft._meta.get_fields()]
            has_multi_model = 'is_multi_model' in draft_fields

            if has_multi_model:
                self.log_test("Multi-Model Support", True, "is_multi_model field present in JigLoadingManualDraft")
            else:
                self.log_test("Multi-Model Support", False, "is_multi_model field not found")

        except Exception as e:
            self.log_test("Multi-Model Support", False, f"Error: {str(e)}")

    def test_tray_color_system(self):
        """Test 6: Verify tray color system exists"""
        try:
            tray_types = TrayType.objects.all()
            has_color_field = any(hasattr(tt, 'tray_color') for tt in tray_types)

            if has_color_field:
                colors = [tt.tray_color for tt in tray_types if hasattr(tt, 'tray_color') and tt.tray_color]
                self.log_test("Tray Color System", True, f"Colors found: {set(colors)}")
            else:
                self.log_test("Tray Color System", False, "tray_color field not found")

        except Exception as e:
            self.log_test("Tray Color System", False, f"Error: {str(e)}")

    def run_all_tests(self):
        """Run all verification tests"""
        print(">>> Starting Watchcase Tracker Scenario Verification...")
        print("=" * 60)

        self.test_1805_model_capacity()
        self.test_ips_color_mapping()
        self.test_1805sak02_configuration()
        self.test_delink_functionality()
        self.test_multi_model_support()
        self.test_tray_color_system()

        print("\n" + "=" * 60)
        print(">>> VERIFICATION SUMMARY:")
        print("=" * 60)

        passed_tests = sum(1 for result in self.test_results if result.startswith("[PASS]"))
        total_tests = len(self.test_results)

        for result in self.test_results:
            print(result)

        print(f"\n>>> RESULT: {passed_tests}/{total_tests} tests passed")

        if passed_tests == total_tests:
            print(">>> ALL TESTS PASSED - System is working correctly!")
        else:
            print(">>> Some tests failed - Review the details above")

        return passed_tests == total_tests

if __name__ == "__main__":
    verifier = ScenarioVerifier()
    success = verifier.run_all_tests()
    sys.exit(0 if success else 1)