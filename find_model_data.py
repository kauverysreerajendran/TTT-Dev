#!/usr/bin/env python
"""
Find test records with no_of_model_cases data
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

from Jig_Loading.models import JigCompleted

print("\n[OK] Searching for JigCompleted records with no_of_model_cases data...")

# Find all jigs with model data
jigs_with_data = JigCompleted.objects.exclude(no_of_model_cases__isnull=True).exclude(no_of_model_cases__exact='').order_by('-updated_at')[:10]

print(f"\n[OK] Found {len(jigs_with_data)} records with model data:")
for j in jigs_with_data:
    print(f"   {j.jig_id}: {j.no_of_model_cases}")

total = JigCompleted.objects.exclude(no_of_model_cases__isnull=True).exclude(no_of_model_cases__exact='').count()
print(f"\n[OK] Total JigCompleted with data: {total}")
