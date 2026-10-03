"""Extract divas body."""
import json
import re
with open('fl511_trace_div2.log') as f:
    text = f.read()
# Extract the divas POST body
for m in re.finditer(r'POST: (\{.*?\})', text):
    body = m.group(1)
    print(f'Body: {body}')
    print(f'Length: {len(body)}')
