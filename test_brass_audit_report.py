#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

from django.test import RequestFactory
from ReportsModule.views import download_report

try:
    rf = RequestFactory()
    request = rf.get('/reports_module/download_report/?module=brass-audit')
    response = download_report(request)
    print(f'✅ SUCCESS: Status Code = {response.status_code}')
    print(f'✅ SUCCESS: Content-Type = {response.get("Content-Type", "Not set")}')
    print(f'✅ SUCCESS: Content-Disposition = {response.get("Content-Disposition", "Not set")}')
    print(f'✅ Report generated successfully - {len(response.content)} bytes')
except Exception as e:
    print(f'❌ ERROR: {type(e).__name__}')
    print(f'❌ Message: {str(e)}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
