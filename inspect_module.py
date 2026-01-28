
import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

from adminportal.models import Module
from django.contrib.auth.models import Group

print("Inspecting Module model fields:")
for field in Module._meta.get_fields():
    print(f"- {field.name} ({type(field).__name__})")

print("\nTrying to filter Module by group:")
try:
    # Just check if the lookup is valid, don't execute query if not needed, but execution is safer
    modules = Module.objects.filter(groups__id=1)
    print("Filter accepted (fields exist).")
except Exception as e:
    print(f"Filter failed: {e}")
