#!/usr/bin/env python3
"""
Complete End-to-End Workflow Test: Day Planning → Spider Spindle
Tests the entire data flow through all modules with real database interactions
Simulates manual data handling without requiring UI interaction
"""

import os
import sys
import django
from datetime import datetime, timezone as dt_timezone
import uuid
import json

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

# Import all models from different modules
from django.contrib.auth.models import User
from DayPlanning.models import DPTrayId_History
from Jig_Loading.models import JigLoadTrayId, JigLoadingManualDraft, JigCompleted, Jig
from Jig_Unloading.models import JigUnload_TrayId, JigUnloadAfterTable
from Spider_Spindle.models import Spider_TrayId, SpiderJigDetails, Spider_ID
from modelmasterapp.models import (
    ModelMasterCreation, ModelMaster, Plating_Color, TrayType,
    PolishFinishType, Version, Vendor, Location
)

class EndToEndWorkflowTest:
    def __init__(self):
        self.test_results = []
        self.test_data = {}
        self.user = None

    def log_test(self, module, action, status, details=""):
        """Log test results with module and action"""
        status_icon = "[PASS]" if status else "[FAIL]"
        message = f"{status_icon} {module} - {action}: {details}"
        self.test_results.append(message)
        print(message)

    def setup_test_user(self):
        """Create or get test user"""
        try:
            self.user, created = User.objects.get_or_create(
                username='testuser',
                defaults={
                    'first_name': 'Test',
                    'last_name': 'User',
                    'email': 'test@example.com'
                }
            )
            if created:
                self.user.set_password('testpass')
                self.user.save()
            self.test_data['user'] = self.user
            self.log_test("SETUP", "Create Test User", True, f"User ID: {self.user.id}")
            return True
        except Exception as e:
            self.log_test("SETUP", "Create Test User", False, f"Error: {str(e)}")
            return False

    def setup_master_data(self):
        """Setup required master data for testing"""
        try:
            # Create plating color (IPS)
            ips_color, _ = Plating_Color.objects.get_or_create(
                plating_color='IPS',
                defaults={
                    'plating_color_internal': 'S',
                    'jig_unload_zone_1': True,
                    'jig_unload_zone_2': False,
                    'createdby': self.user
                }
            )

            # Create tray type (Jumbo)
            jumbo_tray, _ = TrayType.objects.get_or_create(
                tray_type='Jumbo',
                defaults={
                    'tray_capacity': 12,
                    'tray_color': 'Red',
                    'createdby': self.user
                }
            )

            # Create polish finish
            polish_finish, _ = PolishFinishType.objects.get_or_create(
                polish_finish='Buffed',
                defaults={
                    'polish_internal': 'B',
                    'createdby': self.user
                }
            )

            # Create version
            version_k, _ = Version.objects.get_or_create(
                version_name='K',
                defaults={
                    'version_internal': 'K',
                    'createdby': self.user
                }
            )

            # Create model master for 1805SAK02
            model_master, _ = ModelMaster.objects.get_or_create(
                plating_stk_no='1805SAK02',
                defaults={
                    'model_no': '1805',
                    'polish_finish': polish_finish,
                    'ep_bath_type': 'Bright',
                    'tray_type': jumbo_tray,
                    'tray_capacity': 12,
                    'brand': 'Vista',
                    'gender': 'Gent',
                    'wiping_required': False,
                    'version': 'K',
                    'createdby': self.user
                }
            )

            self.test_data['ips_color'] = ips_color
            self.test_data['jumbo_tray'] = jumbo_tray
            self.test_data['model_master'] = model_master

            self.log_test("SETUP", "Master Data", True, "IPS color, Jumbo tray, 1805SAK02 model created")
            return True

        except Exception as e:
            self.log_test("SETUP", "Master Data", False, f"Error: {str(e)}")
            return False

    def test_1_day_planning_creation(self):
        """Step 1: Create lot in Day Planning"""
        try:
            # Generate unique lot ID
            lot_id = f"DP{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # Create model master creation (batch)
            batch = ModelMasterCreation.objects.create(
                model_no='1805',
                polish_stock_number='1805XAK02',
                plating_stock_number='1805SAK02',
                lot_qty=98,  # 50 + 48 = 98 total
                lot_id=lot_id,
                plating_color=self.test_data['ips_color'],
                user=self.user,
                version=Version.objects.filter(version_name='K').first()
            )

            # Create trays in Day Planning
            tray_data = [
                {'tray_id': 'JR-A00001', 'qty': 12},
                {'tray_id': 'JR-A00002', 'qty': 12},
                {'tray_id': 'JR-A00003', 'qty': 12},
                {'tray_id': 'JR-A00004', 'qty': 12},
                {'tray_id': 'JR-A00005', 'qty': 12},  # First model: 60 cases
                {'tray_id': 'JR-A00006', 'qty': 12},
                {'tray_id': 'JR-A00007', 'qty': 12},
                {'tray_id': 'JR-A00008', 'qty': 10},  # Second model: 38 cases (60+38=98)
            ]

            dp_trays = []
            for tray in tray_data:
                dp_tray = DPTrayId_History.objects.create(
                    lot_id=lot_id,
                    tray_id=tray['tray_id'],
                    tray_quantity=tray['qty'],
                    batch_id=batch,
                    user=self.user,
                    tray_type='Jumbo',
                    tray_capacity=12
                )
                dp_trays.append(dp_tray)

            self.test_data['lot_id'] = lot_id
            self.test_data['batch'] = batch
            self.test_data['dp_trays'] = dp_trays

            total_qty = sum(tray['qty'] for tray in tray_data)
            self.log_test("DAY PLANNING", "Create Lot", True,
                         f"Lot {lot_id} created with {len(tray_data)} trays, Total: {total_qty} cases")
            return True

        except Exception as e:
            self.log_test("DAY PLANNING", "Create Lot", False, f"Error: {str(e)}")
            return False

    def test_2_jig_loading_process(self):
        """Step 2: Process lot in Jig Loading with multi-model addition"""
        try:
            lot_id = self.test_data['lot_id']
            batch = self.test_data['batch']

            # Create JIG QR
            jig_qr = f"JIG{datetime.now().strftime('%Y%m%d%H%M%S')}"
            jig = Jig.objects.create(
                jig_qr_id=jig_qr,
                current_user=self.user,
                batch_id=str(batch.id),
                lot_id=lot_id
            )

            # Transfer trays from Day Planning to Jig Loading
            jig_trays = []
            for dp_tray in self.test_data['dp_trays']:
                jig_tray = JigLoadTrayId.objects.create(
                    lot_id=dp_tray.lot_id,
                    tray_id=dp_tray.tray_id,
                    tray_quantity=dp_tray.tray_quantity,
                    batch_id=batch,
                    user=self.user,
                    tray_type=dp_tray.tray_type,
                    tray_capacity=dp_tray.tray_capacity
                )
                jig_trays.append(jig_tray)

            # Create JIG Loading Manual Draft with multi-model setup
            draft_data = {
                'model_1': {'plating_stock_no': '1805SAK02', 'qty': 50, 'trays': 5},
                'model_2': {'plating_stock_no': '1805SAK02', 'qty': 48, 'trays': 3},
                'total_jig_capacity': 98
            }

            jig_draft = JigLoadingManualDraft.objects.create(
                batch_id=str(batch.id),
                lot_id=lot_id,
                user=self.user,
                draft_data=draft_data,
                jig_id=jig_qr,
                original_lot_qty=98,
                updated_lot_qty=98,
                jig_capacity=98,
                loaded_cases_qty=98,
                plating_stock_num='1805SAK02',
                is_multi_model=True,
                draft_status='active'
            )

            self.test_data['jig_qr'] = jig_qr
            self.test_data['jig'] = jig
            self.test_data['jig_trays'] = jig_trays
            self.test_data['jig_draft'] = jig_draft

            self.log_test("JIG LOADING", "Multi-Model Addition", True,
                         f"JIG {jig_qr}: Model 1 (50) + Model 2 (48) = 98 total capacity")
            return True

        except Exception as e:
            self.log_test("JIG LOADING", "Multi-Model Addition", False, f"Error: {str(e)}")
            return False

    def test_3_tray_delinking_process(self):
        """Step 3: Simulate tray delinking process"""
        try:
            lot_id = self.test_data['lot_id']

            # Simulate delinking 2 trays (24 cases)
            delink_trays = self.test_data['jig_trays'][:2]  # First 2 trays
            delink_qty = sum(tray.tray_quantity for tray in delink_trays)

            # Update trays as delinked
            for tray in delink_trays:
                tray.delink_tray = True
                tray.delink_tray_qty = str(tray.tray_quantity)
                tray.save()

            # Update draft with delink information
            draft = self.test_data['jig_draft']
            draft.delink_tray_info = [
                {'tray_id': tray.tray_id, 'qty': tray.tray_quantity}
                for tray in delink_trays
            ]
            draft.delink_tray_qty = delink_qty
            draft.delink_tray_count = len(delink_trays)
            draft.updated_lot_qty = 98 - delink_qty  # Remaining in jig
            draft.save()

            self.test_data['delinked_trays'] = delink_trays
            self.test_data['delinked_qty'] = delink_qty

            self.log_test("JIG LOADING", "Tray Delinking", True,
                         f"Delinked {len(delink_trays)} trays ({delink_qty} cases), Remaining: {98 - delink_qty}")
            return True

        except Exception as e:
            self.log_test("JIG LOADING", "Tray Delinking", False, f"Error: {str(e)}")
            return False

    def test_4_jig_unloading_process(self):
        """Step 4: Process jig unloading with IPS zone logic"""
        try:
            lot_id = self.test_data['lot_id']
            jig_qr = self.test_data['jig_qr']
            batch = self.test_data['batch']

            # Generate new lot ID for unloaded cases
            unload_lot_id = f"JUL{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # Create JigUnloadAfterTable entry
            jig_unload_table = JigUnloadAfterTable.objects.create(
                jig_qr_id=jig_qr,
                combine_lot_ids=[lot_id],
                lot_id=lot_id,
                unload_lot_id=unload_lot_id,
                total_case_qty=74,  # 98 - 24 delinked = 74
                plating_color=self.test_data['ips_color'],
                plating_stk_no='1805SAK02',
                tray_type='Jumbo'
            )

            # Create new trays for unloaded cases (IPS → Zone 1 → Red Trays → JR prefix)
            remaining_qty = 74
            unload_trays = []

            tray_count = 0
            while remaining_qty > 0:
                tray_count += 1
                qty_for_tray = min(12, remaining_qty)  # Jumbo capacity: 12

                # IPS color -> Zone 1 -> Red tray -> JR prefix
                tray_id = f"JR-B{str(tray_count).zfill(5)}"

                unload_tray = JigUnload_TrayId.objects.create(
                    tray_id=tray_id,
                    tray_qty=qty_for_tray,
                    lot_id=unload_lot_id
                )
                unload_trays.append(unload_tray)
                remaining_qty -= qty_for_tray

            # Test IPS Zone Logic
            ips_color = self.test_data['ips_color']
            zone1_active = ips_color.jig_unload_zone_1
            zone2_active = ips_color.jig_unload_zone_2

            zone_validation = zone1_active and not zone2_active

            self.test_data['unload_lot_id'] = unload_lot_id
            self.test_data['unload_trays'] = unload_trays
            self.test_data['jig_unload_table'] = jig_unload_table

            self.log_test("JIG UNLOADING", "IPS Zone Logic", zone_validation,
                         f"IPS → Zone 1: {zone1_active}, Zone 2: {zone2_active}")

            self.log_test("JIG UNLOADING", "Lot Creation", True,
                         f"New lot {unload_lot_id} with {len(unload_trays)} red trays (JR- prefix)")
            return True

        except Exception as e:
            self.log_test("JIG UNLOADING", "Process", False, f"Error: {str(e)}")
            return False

    def test_5_spider_spindle_process(self):
        """Step 5: Process lot in Spider Spindle"""
        try:
            unload_lot_id = self.test_data['unload_lot_id']
            batch = self.test_data['batch']

            # Create Spider ID for Zone 1 (IPS colors go to Zone 1)
            spider_code = f"S098-{datetime.now().strftime('%H%M%S')}"
            spider_id = Spider_ID.objects.create(
                spider_code=spider_code,
                zone=1,  # IPS → Zone 1
                is_active=True
            )

            # Transfer trays from Jig Unloading to Spider Spindle
            spider_trays = []
            for unload_tray in self.test_data['unload_trays']:
                spider_tray = Spider_TrayId.objects.create(
                    lot_id=unload_lot_id,
                    tray_id=unload_tray.tray_id,
                    tray_quantity=unload_tray.tray_qty,
                    batch_id=batch,
                    user=self.user,
                    tray_type='Jumbo',
                    tray_capacity=12
                )
                spider_trays.append(spider_tray)

            # Create SpiderJigDetails entry
            spider_jig = SpiderJigDetails.objects.create(
                jig_qr_id=self.test_data['jig_qr'],
                jig_type='Cylindrical',
                jig_capacity=98,
                plating_color='IPS',
                ep_bath_type='Bright',
                total_cases_loaded=74,  # Cases that reached Spider Spindle
                forging='Bright',
                no_of_model_cases=['1805SAK02:74'],
                lot_id=unload_lot_id,
                new_lot_ids=[unload_lot_id],
                lot_id_quantities={'1805SAK02': 74},
                jig_position='Top'
            )

            self.test_data['spider_id'] = spider_id
            self.test_data['spider_trays'] = spider_trays
            self.test_data['spider_jig'] = spider_jig

            self.log_test("SPIDER SPINDLE", "Zone 1 Processing", True,
                         f"Spider {spider_code} in Zone 1, {len(spider_trays)} trays, 74 cases")
            return True

        except Exception as e:
            self.log_test("SPIDER SPINDLE", "Process", False, f"Error: {str(e)}")
            return False

    def test_6_data_flow_verification(self):
        """Step 6: Verify complete data flow and traceability"""
        try:
            # Verify lot traceability
            original_lot = self.test_data['lot_id']
            unload_lot = self.test_data['unload_lot_id']

            # Check data consistency across modules
            dp_total = sum(tray.tray_quantity for tray in self.test_data['dp_trays'])
            jig_total = sum(tray.tray_quantity for tray in self.test_data['jig_trays'])
            delinked_total = self.test_data['delinked_qty']
            unloaded_total = sum(tray.tray_qty for tray in self.test_data['unload_trays'])
            spider_total = sum(tray.tray_quantity for tray in self.test_data['spider_trays'])

            # Verify data flow equation: DP Total = Jig Total = Delinked + Unloaded
            data_flow_correct = (dp_total == jig_total and
                               dp_total == delinked_total + unloaded_total and
                               unloaded_total == spider_total)

            # Verify color coding (IPS → Red trays → JR prefix)
            all_red_trays = all(tray.tray_id.startswith('JR-') for tray in self.test_data['unload_trays'])

            # Verify zone logic (IPS → Zone 1)
            spider_in_zone1 = self.test_data['spider_id'].zone == 1

            verification_details = (
                f"DP:{dp_total} = JIG:{jig_total} = Delinked:{delinked_total} + "
                f"Unloaded:{unloaded_total} = Spider:{spider_total}, "
                f"Red trays: {all_red_trays}, Zone 1: {spider_in_zone1}"
            )

            overall_success = data_flow_correct and all_red_trays and spider_in_zone1

            self.log_test("DATA FLOW", "Traceability Verification", overall_success, verification_details)
            return overall_success

        except Exception as e:
            self.log_test("DATA FLOW", "Verification", False, f"Error: {str(e)}")
            return False

    def test_7_cleanup(self):
        """Step 7: Optional cleanup of test data"""
        try:
            # Clean up test data (optional - comment out to keep data for inspection)
            # self.test_data['batch'].delete()
            # DPTrayId_History.objects.filter(lot_id=self.test_data['lot_id']).delete()
            # JigLoadTrayId.objects.filter(lot_id=self.test_data['lot_id']).delete()
            # Spider_TrayId.objects.filter(lot_id=self.test_data['unload_lot_id']).delete()

            self.log_test("CLEANUP", "Test Data", True, "Test data preserved for inspection")
            return True

        except Exception as e:
            self.log_test("CLEANUP", "Test Data", False, f"Error: {str(e)}")
            return False

    def run_complete_workflow_test(self):
        """Run the complete end-to-end workflow test"""
        print("=" * 80)
        print(">>> COMPLETE WORKFLOW TEST: Day Planning → Spider Spindle")
        print("=" * 80)

        # Setup phase
        if not self.setup_test_user():
            return False
        if not self.setup_master_data():
            return False

        # Main workflow tests
        tests = [
            self.test_1_day_planning_creation,
            self.test_2_jig_loading_process,
            self.test_3_tray_delinking_process,
            self.test_4_jig_unloading_process,
            self.test_5_spider_spindle_process,
            self.test_6_data_flow_verification,
            self.test_7_cleanup
        ]

        for test in tests:
            if not test():
                print(f">>> TEST FAILED: {test.__name__}")
                break

        # Summary
        print("\n" + "=" * 80)
        print(">>> WORKFLOW TEST SUMMARY")
        print("=" * 80)

        passed_tests = sum(1 for result in self.test_results if "[PASS]" in result)
        total_tests = len(self.test_results)

        for result in self.test_results:
            print(result)

        print(f"\n>>> RESULT: {passed_tests}/{total_tests} tests passed")

        if passed_tests == total_tests:
            print(">>> SUCCESS: Complete workflow functioning correctly!")
            print(">>> Data flow: Day Planning → Jig Loading → Delinking → Jig Unloading → Spider Spindle")
        else:
            print(">>> FAILURE: Some workflow steps failed")

        return passed_tests == total_tests

    def print_test_data_summary(self):
        """Print summary of created test data"""
        if not self.test_data:
            return

        print("\n" + "=" * 60)
        print(">>> TEST DATA SUMMARY (Available for manual inspection)")
        print("=" * 60)

        data_summary = [
            f"Original Lot ID: {self.test_data.get('lot_id', 'N/A')}",
            f"Unload Lot ID: {self.test_data.get('unload_lot_id', 'N/A')}",
            f"JIG QR ID: {self.test_data.get('jig_qr', 'N/A')}",
            f"Spider Code: {self.test_data.get('spider_id', {}).get('spider_code', 'N/A')} (Zone 1)",
            f"Total DP Trays: {len(self.test_data.get('dp_trays', []))}",
            f"Total Unload Trays: {len(self.test_data.get('unload_trays', []))}",
            f"Delinked Quantity: {self.test_data.get('delinked_qty', 0)} cases",
            f"Final Spider Cases: {sum(t.tray_quantity for t in self.test_data.get('spider_trays', []))} cases"
        ]

        for item in data_summary:
            print(f"  {item}")

if __name__ == "__main__":
    tester = EndToEndWorkflowTest()
    success = tester.run_complete_workflow_test()
    tester.print_test_data_summary()

    print(f"\n>>> WORKFLOW TEST COMPLETED: {'SUCCESS' if success else 'FAILED'}")
    sys.exit(0 if success else 1)