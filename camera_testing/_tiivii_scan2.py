import json
import os

cfg = json.load(open(os.environ['TEMP'] + r'\tiivii_cfg.json', encoding='utf-8'))
cams = cfg['cameras']
print('cams:', len(cams))
print('keys:', sorted(cams[0].keys()))
print(json.dumps(cams[0], ensure_ascii=False, indent=1)[:2500])
