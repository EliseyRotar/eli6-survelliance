import json
import os
import re
import urllib.request

TEMP = os.environ['TEMP']
node = json.load(open(TEMP + r'\gijon_drupal.json', encoding='utf-8'))
paras = node.get('field_bloques_de_contenido') or []
ids = [p['target_id'] for p in paras]
print('paragraph ids:', ids)

ids_expr = '|'.join('(%d)' % i for i in ids)
url = ('https://drupal.gijon.es/es/detalle_paragraph/?_format=json&id_padre=4508'
       '&idioma=es&sin_tipo[0]=preguntas_frecuentes&ids=' + ids_expr)
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=40) as r:
    body = r.read()
    print('status', r.status, 'len', len(body))
open(TEMP + r'\gijon_paras.json', 'wb').write(body)

data = json.loads(body.decode('utf-8'))
print('type', type(data))
if isinstance(data, dict):
    print('keys', list(data.keys())[:30])

txt = json.dumps(data, ensure_ascii=False)
# hunt for youtube ids / cam markers
for pat in (r'youtu', r'camstreamer', r'm3u8', r'webcam', r'camara'):
    print(pat, len(re.findall(pat, txt, re.I)))
print(txt[:3000])
