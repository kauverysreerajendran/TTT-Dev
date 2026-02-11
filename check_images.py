import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
import django
django.setup()
from modelmasterapp.models import ModelMaster

plating_stk_nos = ['1805QSP02/GUN', '1805XSP02', '1805QCL02/GUN', '1805XCL02']

for stk in plating_stk_nos:
    mm = ModelMaster.objects.filter(plating_stk_no=stk).first()
    if mm:
        images = [img.master_image.url for img in mm.images.all()]
        print(f'{stk}: {len(images)} images - {images}')
    else:
        print(f'{stk}: No ModelMaster found')