#!/usr/bin/env python3
import re

with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\wiredny_webcam.html', encoding='utf-8') as f:
    h = f.read()

# Print full page
print(h)