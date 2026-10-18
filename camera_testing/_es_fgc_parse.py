# -*- coding: utf-8 -*-
import json

meta = json.load(open(r"C:\Users\ELI6-A~1\AppData\Local\Temp\fgc_ods_meta.json", encoding="utf-8"))
rows = json.load(open(r"C:\Users\ELI6-A~1\AppData\Local\Temp\fgc_ods_rows.json", encoding="utf-8"))

ds = meta.get("dataset", meta)
print("dataset id:", ds.get("dataset_id"), "| records:", ds.get("records_count"))
fields = (ds.get("fields_schema") or ds.get("fields") or [])
for f in fields[:40]:
    print("  field:", f.get("name"), "|", f.get("label"), "|", f.get("type"))

res = rows.get("results", [])
print("returned:", len(res), "total:", rows.get("total_count"))
for rec in res[:5]:
    print(json.dumps(rec, ensure_ascii=False)[:420])
    print("---")
