
import os
import django
import sys

sys.path.append('c:/Users/deepa/OneDrive/Desktop/Aishu/pinesphere/TTT-Jan2026')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

from IQF.models import IQFTrayId
from DayPlanning.models import DPTrayId_History
from InputScreening.models import IPTrayId
from Brass_QC.models import BrassTrayId

lot_id = "LID180220261617190001"

print(f"LOT: {lot_id}")
print("BRASS_TRAYS:", list(BrassTrayId.objects.filter(lot_id=lot_id).values_list('tray_id', flat=True)))
print("IP_TRAYS:", list(IPTrayId.objects.filter(lot_id=lot_id).values_list('tray_id', flat=True)))
print("DP_HISTORY:", list(DPTrayId_History.objects.filter(lot_id=lot_id).values_list('tray_id', flat=True)))
print("IQF_TRAYS:", list(IQFTrayId.objects.filter(lot_id=lot_id).values_list('tray_id', flat=True)))
