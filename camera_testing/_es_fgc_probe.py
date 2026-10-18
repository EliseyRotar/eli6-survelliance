# -*- coding: utf-8 -*-
import json
import re

d = json.load(open(r"C:\Users\ELI6-A~1\AppData\Local\Temp\fgc_meta.json", encoding="utf-8"))
for k in ("name", "displayType", "blobId", "attachments", "metadata", "childViews", "viewType", "blobFilename"):
    v = d.get(k)
    if isinstance(v, (dict, list)):
        v = json.dumps(v, ensure_ascii=False)[:400]
    print(k, "=", v)
s = json.dumps(d, ensure_ascii=False)
print("--- urls ---")
for m in sorted(set(re.findall(r"https?://[^\"\\ ]+", s)))[:25]:
    print(" ", m[:160])
print("--- keys ---")
print(sorted(d.keys()))
