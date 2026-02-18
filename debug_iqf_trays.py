
import os
import django
import sys

# Setup Django environment
sys.path.append('c:/Users/deepa/OneDrive/Desktop/Aishu/pinesphere/TTT-Jan2026')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

from IQF.models import IQFTrayId, IQF_Rejected_TrayScan
from DayPlanning.models import DPTrayId_History
from InputScreening.models import IPTrayId
from Brass_QC.models import BrassTrayId

lot_id = "LID180220261617190001"

print(f"--- Debugging Tray IDs for Lot: {lot_id} ---")

print("\n1. IQFTrayId (Current):")
iqf_trays = IQFTrayId.objects.filter(lot_id=lot_id)
print(f"   Count: {iqf_trays.count()}")
for t in iqf_trays:
    print(f"   - {t.tray_id} (Rejected: {t.rejected_tray}, Delink: {t.delink_tray}, IP_verified: {t.IP_tray_verified})")

print("\n2. DPTrayId_History:")
history_trays = DPTrayId_History.objects.filter(lot_id=lot_id)
print(f"   Count: {history_trays.count()}")
for t in history_trays:
    print(f"   - {t.tray_id} (IP_verified: {t.IP_tray_verified})")

print("\n3. IPTrayId:")
ip_trays = IPTrayId.objects.filter(lot_id=lot_id)
print(f"   Count: {ip_trays.count()}")
for t in ip_trays:
    print(f"   - {t.tray_id} (Delink: {t.delink_tray})")

print("\n4. BrassTrayId:")
brass_trays = BrassTrayId.objects.filter(lot_id=lot_id)
print(f"   Count: {brass_trays.count()}")
for t in brass_trays:
    print(f"   - {t.tray_id}")

print("\n5. IQF_Rejected_TrayScan:")
scan_rejections = IQF_Rejected_TrayScan.objects.filter(lot_id=lot_id)
print(f"   Count: {scan_rejections.count()}")
for r in scan_rejections:
    print(f"   - Tray: '{r.tray_id}' Qty: {r.rejected_tray_quantity}")
