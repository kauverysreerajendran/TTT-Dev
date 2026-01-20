#!/usr/bin/env python
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

from Inprocess_Inspection.views import InprocessInspectionView
from django.test import RequestFactory

# Create a test request
factory = RequestFactory()
request = factory.get('/inprocess_inspection_main/')
view = InprocessInspectionView()
view.request = request

# Get context data
context = view.get_context_data()

# Check jig_details
jig_details = context.get('jig_details', [])
print(f'Number of jig_details: {len(jig_details)}')

for jig in jig_details[:3]:  # First 3
    print(f'Jig ID: {jig.id}, lot_id: {jig.lot_id}')
    print(f'  plating_stock_num: {getattr(jig, "plating_stock_num", None)}')
    print(f'  no_of_model_cases: {getattr(jig, "no_of_model_cases", None)}')
    print(f'  model_colors: {getattr(jig, "model_colors", {})}')
    print(f'  model_images keys: {list(getattr(jig, "model_images", {}).keys())}')
    print()