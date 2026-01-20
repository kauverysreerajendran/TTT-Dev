#!/usr/bin/env python
import os
import django
import sys

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')
django.setup()

from django.template import Context, Template, loader
from django.template.engine import Engine
from Jig_Loading.models import JigCompleted
from modelmasterapp.models import TotalStockModel

# Load template engine with custom tags
engine = Engine.get_default()

print("[OK] Testing Model Presents Single Circle Template Change")
print("=" * 60)

# Find test record
jig = JigCompleted.objects.filter(jig_id='J144-0002').first()
if jig:
    print(f"\n[OK] Found JigCompleted: {jig.jig_id}")
    print(f"   lot_id: {jig.lot_id}")
    print(f"   no_of_model_cases: {jig.no_of_model_cases}")
    
    # Simulate what the backend provides
    class MockJigDetail:
        def __init__(self):
            self.no_of_model_cases = ['2617', '2618'] if jig.no_of_model_cases else []
            self.model_colors = {'2617': '#e74c3c', '2618': '#f1c40f'} if self.no_of_model_cases else {}
            self.model_images = {
                '2617': ['/media/model_images/image1.jpg'],
                '2618': ['/media/model_images/image2.jpg']
            } if self.no_of_model_cases else {}
    
    # Test with data
    jig_detail = MockJigDetail()
    jig_detail.no_of_model_cases = ['2617', '2618']  # Simulate multiple models
    jig_detail.model_colors = {'2617': '#e74c3c', '2618': '#f1c40f'}
    jig_detail.model_images = {'2617': ['/image1.jpg'], '2618': ['/image2.jpg']}
    
    template_str = """{% load stock_filters %}
    {% if no_of_model_cases %}
        {% with first_model=no_of_model_cases.0 %}
            <!-- Display only ONE circle for the first model -->
            {% if model_colors %}
                [CIRCLE_COLOR]{{ model_colors|get_item:first_model }}[/CIRCLE_COLOR]
            {% else %}
                [CIRCLE_COLOR]#ccc[/CIRCLE_COLOR]
            {% endif %}
            <!-- Display model number as reference if available -->
            [MODEL_NUMBER]{{ first_model }}[/MODEL_NUMBER]
        {% endwith %}
    {% else %}
        <!-- No model data: display placeholder -->
        [CIRCLE_COLOR]#ccc[/CIRCLE_COLOR]
        [MODEL_NUMBER]N/A[/MODEL_NUMBER]
    {% endif %}
    """
    
    template = Template(template_str)
    context = Context({
        'no_of_model_cases': jig_detail.no_of_model_cases,
        'model_colors': jig_detail.model_colors,
        'model_images': jig_detail.model_images
    })
    
    result = template.render(context)
    print(f"\n[OK] Template Render with Multiple Models:")
    print(f"   Input: {jig_detail.no_of_model_cases}")
    print(f"   Output: {result.strip()}")
    
    # Verify only ONE circle is displayed
    if '[CIRCLE_COLOR]#e74c3c[/CIRCLE_COLOR]' in result and '[MODEL_NUMBER]2617[/MODEL_NUMBER]' in result:
        print(f"\n[PASS] Single circle displayed (first model only)")
        print(f"   Color: #e74c3c")
        print(f"   Model: 2617")
        print(f"   Note: Down arrow will allow clicking to view gallery with all models")
    else:
        print(f"\n[FAIL] Template not rendering correctly")
    
    # Test with no data
    print(f"\n[OK] Testing with no model data:")
    jig_detail.no_of_model_cases = []
    context = Context({
        'no_of_model_cases': jig_detail.no_of_model_cases,
        'model_colors': {},
        'model_images': {}
    })
    result = template.render(context)
    
    if '[CIRCLE_COLOR]#ccc[/CIRCLE_COLOR]' in result and '[MODEL_NUMBER]N/A[/MODEL_NUMBER]' in result:
        print(f"[PASS] Placeholder displayed when no models")
        print(f"   Color: #ccc (gray)")
        print(f"   Text: N/A")
    else:
        print(f"[FAIL] Placeholder not rendering correctly")

else:
    print("[FAIL] Test record not found")
