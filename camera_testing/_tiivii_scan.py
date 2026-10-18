import json
import os

cfg = json.load(open(os.environ['TEMP'] + r'\tiivii_cfg.json', encoding='utf-8'))
print('top keys:', sorted(cfg.keys()))
for k, v in cfg.items():
    if isinstance(v, list):
        print(' list', k, len(v))
    elif isinstance(v, dict):
        print(' dict', k, sorted(v.keys())[:12])
    else:
        print(' scalar', k, '=', str(v)[:100])
