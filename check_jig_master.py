import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

from Jig_Loading.models import JigLoadingMaster
from modelmasterapp.models import ModelMaster, ModelMasterCreation

print('JigLoadingMaster entries:')
for j in JigLoadingMaster.objects.all():
    print(f'{j.model_stock_no} - {j.model_stock_no.model_no} - {j.jig_type} - {j.jig_capacity}')

print('\nModelMaster entries for 1805NAK02:')
for m in ModelMaster.objects.filter(model_no='1805NAK02'):
    print(f'ID: {m.pk}, Model: {m}, model_no: {m.model_no}')

print('\nModelMasterCreation entries for 1805NAK02:')
for mmc in ModelMasterCreation.objects.filter(model_stock_no__model_no='1805NAK02')[:5]:
    print(f'MMC ID: {mmc.pk}, model_stock_no ID: {mmc.model_stock_no.pk}, model_no: {mmc.model_stock_no.model_no}')