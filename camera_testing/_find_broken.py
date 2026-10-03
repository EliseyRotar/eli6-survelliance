"""Identify and report rows with wrong column count (likely due to unquoted commas in notes).

Such rows need to be reconstructed by combining notes across the broken columns.
"""
import csv
import os
import sys

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
csv.field_size_limit(2**31 - 1)

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
BACKUP_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\backups\controllable_Webcams_broken_rows.csv'

with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
    rows = list(csv.reader(f))

header = rows[0]
ncols = len(header)
print(f'Header: {ncols} cols')
print(f'Total rows: {len(rows)}')

bad_indices = []
for i, r in enumerate(rows):
    if len(r) != ncols:
        bad_indices.append((i, len(r)))

print(f'Bad rows: {len(bad_indices)}')
for i, c in bad_indices[:20]:
    print(f'  row {i}: {c} cols, preview: {rows[i][:3]}')
