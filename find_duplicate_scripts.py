import re

with open(r'static/templates/Input_Screening/IS_PickTable.html', 'r', encoding='utf-8') as f:
    html = f.read()

scripts = re.findall(r'<script.*?>(.*?)</script>', html, re.DOTALL)
seen = set()
for idx, script in enumerate(scripts):
    norm = script.strip()
    if norm in seen:
        print(f"Duplicate script block at index {idx}")
    else:
        seen.add(norm)