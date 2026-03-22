#!/usr/bin/env python3
"""
Manual Workflow Data Creation Test
Creates actual test data that demonstrates the complete workflow
Run this to create test data, then inspect it manually in Django admin
"""

import os
import sys
import django
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

from django.contrib.auth.models import User
from DayPlanning.models import DPTrayId_History
from Jig_Loading.models import JigLoadTrayId, JigLoadingManualDraft, Jig
from Jig_Unloading.models import JigUnload_TrayId, JigUnloadAfterTable
from Spider_Spindle.models import Spider_TrayId, SpiderJigDetails, Spider_ID
from modelmasterapp.models import (
    ModelMasterCreation, ModelMaster, Plating_Color, TrayType
)

def create_workflow_test_data():
    """Create complete workflow test data for manual inspection"""
    print("Creating Workflow Test Data...")

    # Get or create test user
    user, created = User.objects.get_or_create(
        username='workflow_test',
        defaults={'first_name': 'Workflow', 'last_name': 'Tester'}
    )

    # Generate unique identifiers
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    lot_id = f"WF_{timestamp}"
    jig_qr = f"JIG_{timestamp}"
    unload_lot_id = f"JUL_{timestamp}"
    spider_code = f"S098-{timestamp[-6:]}"

    print(f"Test Lot ID: {lot_id}")
    print(f"JIG QR: {jig_qr}")
    print(f"Unload Lot ID: {unload_lot_id}")
    print(f"Spider Code: {spider_code}")

    # Get 1805SAK02 model
    model_1805 = ModelMaster.objects.filter(plating_stk_no='1805SAK02').first()
    if not model_1805:
        print("ERROR: 1805SAK02 model not found. Run add_jig_loading_master.py first")
        return False

    # Get IPS color
    ips_color = Plating_Color.objects.filter(plating_color='IPS').first()
    if not ips_color:
        print("ERROR: IPS color not found")
        return False

    try:
        # Step 1: Create Day Planning data
        print("\n1. Creating Day Planning data...")
        batch = ModelMasterCreation.objects.create(
            model_no='1805',
            plating_stock_number='1805SAK02',
            lot_qty=98,
            lot_id=lot_id,
            plating_color=ips_color,
            user=user
        )

        # Create Day Planning trays
        dp_trays_data = [
            ('JR-T00001', 12), ('JR-T00002', 12), ('JR-T00003', 12),
            ('JR-T00004', 12), ('JR-T00005', 12),  # Model 1: 60 cases
            ('JR-T00006', 12), ('JR-T00007', 12), ('JR-T00008', 14)   # Model 2: 38 cases
        ]

        dp_trays = []
        for tray_id, qty in dp_trays_data:
            dp_tray = DPTrayId_History.objects.create(
                lot_id=lot_id,
                tray_id=tray_id,
                tray_quantity=qty,
                batch_id=batch,
                user=user,
                tray_type='Jumbo',
                tray_capacity=12
            )
            dp_trays.append(dp_tray)

        print(f"   Created {len(dp_trays)} Day Planning trays")

        # Step 2: Transfer to Jig Loading
        print("\n2. Creating Jig Loading data...")

        # Create JIG
        jig = Jig.objects.create(
            jig_qr_id=jig_qr,
            current_user=user,
            batch_id=str(batch.id),
            lot_id=lot_id
        )

        # Transfer trays to Jig Loading
        jl_trays = []
        for dp_tray in dp_trays:
            jl_tray = JigLoadTrayId.objects.create(
                lot_id=dp_tray.lot_id,
                tray_id=dp_tray.tray_id,
                tray_quantity=dp_tray.tray_quantity,
                batch_id=batch,
                user=user
            )
            jl_trays.append(jl_tray)

        # Create multi-model draft
        draft_data = {
            'model_1': {'plating_stock_no': '1805SAK02', 'qty': 50},
            'model_2': {'plating_stock_no': '1805SAK02', 'qty': 48},
            'jig_capacity': 98
        }

        jig_draft = JigLoadingManualDraft.objects.create(
            batch_id=str(batch.id),
            lot_id=lot_id,
            user=user,
            draft_data=draft_data,
            jig_id=jig_qr,
            original_lot_qty=98,
            updated_lot_qty=98,
            jig_capacity=98,
            is_multi_model=True,
            draft_status='active'
        )

        print(f"   Created JIG Loading with {len(jl_trays)} trays")
        print(f"   Multi-model: Model 1 (50) + Model 2 (48) = 98 total")

        # Step 3: Simulate delinking
        print("\n3. Simulating tray delinking...")

        # Delink first 2 trays (24 cases)
        delinked_trays = jl_trays[:2]
        delinked_qty = sum(t.tray_quantity for t in delinked_trays)

        for tray in delinked_trays:
            tray.delink_tray = True
            tray.delink_tray_qty = str(tray.tray_quantity)
            tray.save()

        # Update draft
        jig_draft.delink_tray_qty = delinked_qty
        jig_draft.delink_tray_count = len(delinked_trays)
        jig_draft.updated_lot_qty = 98 - delinked_qty
        jig_draft.save()

        remaining_qty = 98 - delinked_qty
        print(f"   Delinked {len(delinked_trays)} trays ({delinked_qty} cases)")
        print(f"   Remaining for unloading: {remaining_qty} cases")

        # Step 4: Create Jig Unloading data
        print("\n4. Creating Jig Unloading data...")

        # Create unloading table entry
        unload_table = JigUnloadAfterTable.objects.create(
            jig_qr_id=jig_qr,
            combine_lot_ids=[lot_id],
            lot_id=lot_id,
            unload_lot_id=unload_lot_id,
            total_case_qty=remaining_qty,
            plating_color=ips_color,
            plating_stk_no='1805SAK02'
        )

        # Create new red trays for unloaded cases (IPS → Zone 1 → Red → JR-)
        unload_trays = []
        cases_left = remaining_qty
        tray_num = 1

        while cases_left > 0:
            qty_this_tray = min(12, cases_left)  # Jumbo capacity
            tray_id = f"JR-U{str(tray_num).zfill(5)}"

            unload_tray = JigUnload_TrayId.objects.create(
                tray_id=tray_id,
                tray_qty=qty_this_tray,
                lot_id=unload_lot_id
            )
            unload_trays.append(unload_tray)
            cases_left -= qty_this_tray
            tray_num += 1

        print(f"   Created {len(unload_trays)} red trays (JR- prefix) for {remaining_qty} cases")

        # Step 5: Create Spider Spindle data
        print("\n5. Creating Spider Spindle data...")

        # Create Spider ID for Zone 1 (IPS goes to Zone 1)
        spider_id = Spider_ID.objects.create(
            spider_code=spider_code,
            zone=1,
            is_active=True
        )

        # Transfer trays to Spider Spindle
        spider_trays = []
        for unload_tray in unload_trays:
            spider_tray = Spider_TrayId.objects.create(
                lot_id=unload_lot_id,
                tray_id=unload_tray.tray_id,
                tray_quantity=unload_tray.tray_qty,
                batch_id=batch,
                user=user
            )
            spider_trays.append(spider_tray)

        # Create Spider Jig Details
        spider_jig = SpiderJigDetails.objects.create(
            jig_qr_id=jig_qr,
            jig_type='Cylindrical',
            jig_capacity=98,
            plating_color='IPS',
            ep_bath_type='Bright',
            total_cases_loaded=remaining_qty,
            forging='Bright',
            lot_id=unload_lot_id,
            jig_position='Top'
        )

        print(f"   Created Spider ID {spider_code} in Zone 1")
        print(f"   Transferred {len(spider_trays)} trays to Spider Spindle")

        # Summary
        print(f"\n=== WORKFLOW SUMMARY ===")
        print(f"Original Lot: {lot_id} (98 cases)")
        print(f"JIG QR: {jig_qr}")
        print(f"Delinked: {delinked_qty} cases")
        print(f"Unloaded Lot: {unload_lot_id} ({remaining_qty} cases)")
        print(f"Spider Code: {spider_code} (Zone 1)")
        print(f"Final Trays: {len(spider_trays)} red trays (JR- prefix)")

        print(f"\n=== DATA FLOW VERIFICATION ===")
        print(f"Day Planning: {len(dp_trays)} trays → Jig Loading: {len(jl_trays)} trays")
        print(f"Delinked: {len(delinked_trays)} trays → Unloaded: {len(unload_trays)} trays")
        print(f"Spider Spindle: {len(spider_trays)} trays")
        print(f"IPS Color → Zone 1 → Red Trays (JR-) ✓")

        print(f"\n=== SUCCESS ===")
        print(f"Complete workflow test data created!")
        print(f"You can now inspect this data in Django admin or database")

        return True

    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    success = create_workflow_test_data()
    sys.exit(0 if success else 1)