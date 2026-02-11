import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
import django
django.setup()
from modelmasterapp.models import ModelMasterCreation

plating_stk_nos = ['1805QSP02/GUN', '1805QCL02/GUN', '1805WBK02', '1805QBK02/GUN', '1805NAR02', '1805YAK02/2N', '1805WAK02', '1805SAK02', '1805NAK02']

for stk in plating_stk_nos:
    mmc = ModelMasterCreation.objects.filter(plating_stk_no=stk).first()
    if mmc:
        images = [img.master_image.url for img in mmc.images.all()]
        print(f'{stk} (batch: {mmc.batch_id}): {len(images)} images - {images[:3]}...')  # Show first 3
    else:
        print(f'{stk}: No ModelMasterCreation found')