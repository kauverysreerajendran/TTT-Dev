import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
import django
django.setup()
from modelmasterapp.models import ModelMasterCreation, ModelImage

# Get all ModelImage
all_images = list(ModelImage.objects.all())
print(f'Found {len(all_images)} images to associate.')

# Get all ModelMasterCreation
mmcs = ModelMasterCreation.objects.all()
print(f'Found {len(mmcs)} ModelMasterCreation instances.')

for mmc in mmcs:
    current_images = list(mmc.images.all())
    for img in all_images:
        if img not in current_images:
            mmc.images.add(img)
            print(f'Added {img.master_image.url} to {mmc.batch_id}')

print('Association complete.')