# -*- coding: utf-8 -*-
"""Session 47: build unified inventory of new Spain/Andorra cameras (not yet in CSV)."""
import json
import os
import re

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
CSV = r"C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv"

# INE province codes (old dgt json uses 1..51)
INE = {"1": "Álava", "2": "Albacete", "3": "Alicante", "4": "Almería", "5": "Ávila",
       "6": "Badajoz", "7": "Illes Balears", "8": "Barcelona", "9": "Burgos", "10": "Cáceres",
       "11": "Cádiz", "12": "Castellón", "13": "Ciudad Real", "14": "Córdoba", "15": "A Coruña",
       "16": "Cuenca", "17": "Girona", "18": "Granada", "19": "Guadalajara", "20": "Huelva",
       "21": "Huesca", "22": "Jaén", "23": "León", "24": "Lleida", "25": "La Rioja", "26": "Lugo",
       "27": "Madrid", "28": "Málaga", "29": "Murcia", "30": "Navarra", "31": "Ourense",
       "32": "Asturias", "33": "Palencia", "34": "Las Palmas", "35": "Pontevedra",
       "36": "Salamanca", "37": "S.C. Tenerife", "38": "Cantabria", "39": "Segovia",
       "40": "Sevilla", "41": "Soria", "42": "Tarragona", "43": "Teruel", "44": "Toledo",
       "45": "Valencia", "46": "Valladolid", "47": "Bizkaia", "48": "Zamora", "49": "Zaragoza",
       "50": "Ceuta", "51": "Melilla"}


def jload(name):
    return json.load(open(os.path.join(ROOT, name), encoding="utf-8"))


def fnum(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def okgeo(lat, lon, lo=(-10.5, 5.0), la=(34.5, 44.5)):
    return lat is not None and lon is not None and lo[0] <= lon <= lo[1] and la[0] <= lat <= la[1]


# ---- DATEX2 index (id -> {province, road, dir, lastUpdate, lat, lon, pk, dest}) ----
datex = {}
xml = open(os.path.join(ROOT, "_es_datex2_v37.xml"), encoding="utf-8", errors="replace").read()
for blk in re.split(r"<ns2:device\b", xml)[1:]:
    m_id = re.search(r'id="(\d+)"', blk)
    if not m_id:
        continue
    d = {}
    m = re.search(r"<lse:province>([^<]+)</lse:province>", blk)
    if m:
        d["province"] = m.group(1).strip()
    m = re.search(r"<loc:roadName>([^<]+)</loc:roadName>", blk)
    if m:
        d["road"] = m.group(1).strip()
    m = re.search(r"<loc:tpegDirection>([^<]+)</loc:tpegDirection>", blk)
    if m:
        d["tpeg"] = m.group(1).strip()
    m = re.search(r"<lse:tpegDirectionRoad>([^<]+)</lse:tpegDirectionRoad>", blk)
    if m:
        d["dir"] = m.group(1).strip()
    m = re.search(r"<ns2:lastUpdateOfDeviceInformation>([^<]+)<", blk)
    if m:
        d["lastUpdate"] = m.group(1).strip()
    m = re.search(r"<loc:latitude>([^<]+)</loc:latitude>", blk)
    if m:
        d["lat"] = m.group(1).strip()
    m = re.search(r"<loc:longitude>([^<]+)</loc:longitude>", blk)
    if m:
        d["lon"] = m.group(1).strip()
    m = re.search(r"<lse:kilometerPoint>([^<]+)</lse:kilometerPoint>", blk)
    if m:
        d["pk"] = m.group(1).strip()
    datex[m_id.group(1)] = d

# ---- sources ----
prod = {c["idCamara"]: c for c in jload("_es_camaras_etraffic.json")["camaras"]}
pre = {c["idCamara"]: c for c in jload("_es_camaras_pre.json")["camaras"]}
old = {c["id"]: c for c in jload("_es_camaras_dgt.json")["camaras"]}
already = jload("_es_dgt_already.json")
have_ids = set(already)

inv = []
report = []


def add(e):
    inv.append(e)


# ============ 1) DGT missing 41 ============
old_only = ["168856", "176531", "176532", "176533", "176534", "176535", "176537",
            "178574", "181921", "181924"]
cdx_only = ["18", "103", "1040"]
our_ids = set(prod) | {"993"} | set(old_only) | set(cdx_only)
missing = sorted(our_ids - have_ids, key=int)
report.append(f"DGT missing from CSV: {len(missing)}")

for cid in missing:
    src = None
    road = pk = sentido = lat = lon = None
    prov_name = None
    extra = []
    if cid in prod:
        c = prod[cid]
        src = "etraffic-camaras-api"
        road, pk, sentido = c.get("carretera"), c.get("pk"), c.get("sentido")
        lon, lat = fnum(c.get("coordX")), fnum(c.get("coordY"))
    elif cid in pre:
        c = pre[cid]
        src = "etraffic-pre-env-api"
        road, pk, sentido = c.get("carretera"), c.get("pk"), c.get("sentido")
        lon, lat = fnum(c.get("coordX")), fnum(c.get("coordY"))
        extra.append("pre-env")
    elif cid in old:
        c = old[cid]
        src = "dgt-camaras-json-legacy"
        road, pk, sentido = c.get("carretera"), fnum(c.get("pk")), c.get("sentido")
        lat, lon = fnum(c.get("latitud")), fnum(c.get("longitud"))
        prov_name = INE.get(str(c.get("provincia") or "").strip())
        if c.get("fecha"):
            extra.append("fecha=" + c["fecha"])
        if cid == "176531" and lat and lat < 0:
            lat = abs(lat)
            extra.append("coord-sign-fixed")
        if cid == "181924":
            # latitud '40,23368' handled by fnum comma replace; lon already ok
            extra.append("coord-comma-parsed")
    else:
        src = "wayback-cdx-only"
    dx = datex.get(cid, {})
    if not prov_name:
        prov_name = dx.get("province")
    if not road:
        road = dx.get("road")
    if not pk and dx.get("pk"):
        pk = fnum(dx["pk"])
    notes = [f"source={src}"]
    if road:
        notes.append(f"road={road}")
    if pk is not None:
        notes.append(f"pk={pk}")
    if sentido:
        notes.append(f"sentido={sentido}")
    if dx.get("lastUpdate"):
        notes.append("datex2_lastUpdate=" + dx["lastUpdate"])
    if dx.get("dir"):
        notes.append("datex2_dir=" + dx["dir"])
    notes += extra
    if cid == "18":
        notes.append("stale-image-lm-2026-05-05")
    if not okgeo(lat, lon):
        notes.append("no-coordinates")
        lat = lon = None
    name = f"{road} km {pk}" if road and pk is not None else f"DGT eTraffic cam {cid}"
    add({
        "key": f"dgt-{cid}", "prefix": "dgt", "project_name": name,
        "url": "https://etraffic.dgt.es/etrafficWEB/",
        "image_url": f"https://etraffic.dgt.es/camarasEtraffic/{cid}.jpg",
        "type": "image", "category": "traffic", "country": "Spain",
        "region": prov_name or "", "city": "", "road": road or "",
        "lat": lat, "lon": lon, "geo_source": "host:etraffic.dgt.es",
        "location_precision": "precise" if lat is not None else "",
        "live_status": "", "http_status": "", "content_type": "", "last_modified": "",
        "notes": "; ".join(notes),
    })

# ============ 2) Euskadi GV (trafikoa) ============
ej = jload("_es_euskadi.geojson")
eusk_seen = set()
for f in ej["features"]:
    p = f["properties"]
    img = p.get("url cam") or ""
    if not img or img in eusk_seen:
        continue
    eusk_seen.add(img)
    lon, lat = f["geometry"]["coordinates"][:2]
    road, pk, title = p.get("road") or "", p.get("pk") or "", p.get("title") or ""
    name = f"{road} km {pk} ({title})".replace("()", "").strip() if road else title
    add({
        "key": "eusk-" + re.sub(r"\D", "", img) or "eusk-x", "prefix": "eusk",
        "project_name": name,
        "url": "https://opendata.euskadi.eus/catalogo/-/camaras-de-trafico-de-las-administraciones-publicas-de-euskadi/",
        "image_url": img, "type": "image", "category": "traffic", "country": "Spain",
        "region": "Euskadi", "city": title, "road": road,
        "lat": lat, "lon": lon, "geo_source": "src:opendata.euskadi.eus",
        "location_precision": "precise",
        "live_status": "", "http_status": "", "content_type": "", "last_modified": "",
        "notes": f"source=opendata-euskadi-geojson; title={title}; pk={pk}; img-host-trafikoa-unreachable-expected",
    })
report.append(f"Euskadi GV: {len(eusk_seen)}")

# ============ 3) Vitoria-Gasteiz ============
vj = jload("_es_vitoria.geojson")
n_vit = 0
for f in vj["features"]:
    p = f["properties"]
    img = p.get("imagen") or ""
    if not img:
        continue
    n_vit += 1
    lon, lat = f["geometry"]["coordinates"][:2]
    nombre = p.get("nombre") or ""
    notes = ["source=vitoria-gasteiz-cameras-geojson",
             f"comm={p.get('commStatusCode')}", f"oper={p.get('operStatusCode')}",
             f"camId={f.get('id')}"]
    add({
        "key": "vit-" + str(f.get("id")), "prefix": "vit",
        "project_name": nombre,
        "url": "https://www.vitoria-gasteiz.org/c11-01w/cameras?action=list&format=GEOJSON",
        "image_url": img, "type": "image", "category": "traffic", "country": "Spain",
        "region": "Álava", "city": "Vitoria-Gasteiz", "road": "",
        "lat": lat, "lon": lon, "geo_source": "src:vitoria-gasteiz.org",
        "location_precision": "precise",
        "live_status": "", "http_status": "", "content_type": "", "last_modified": "",
        "notes": "; ".join(notes),
    })
report.append(f"Vitoria: {n_vit}")

# ============ 4) Catalonia (WFS XML, coords) ============
xs = open(os.path.join(ROOT, "_es_cat_xml.xml"), encoding="utf-8", errors="replace").read()
n_cat = 0
for blk in re.findall(r"<gml:featureMember>.*?</gml:featureMember>", xs, re.S):
    m_c = re.search(r"<gml:coordinates[^>]*>([^<]+)</gml:coordinates>", blk)
    m_l = re.search(r"<cite:link>([^<]+)</cite:link>", blk)
    if not (m_c and m_l):
        continue
    lon_s, lat_s = m_c.group(1).strip().split(",")[:2]
    lon, lat = float(lon_s), float(lat_s)
    link = m_l.group(1).strip()
    road = (re.search(r"<cite:carretera>([^<]+)<", blk) or type("", (), {"group": lambda s, i: ""})()).group(1)
    mun = (re.search(r"<cite:municipi>([^<]+)<", blk) or type("", (), {"group": lambda s, i: ""})()).group(1)
    pk = (re.search(r"<cite:pk>([^<]+)<", blk) or type("", (), {"group": lambda s, i: ""})()).group(1)
    font = (re.search(r"<cite:font>([^<]+)<", blk) or type("", (), {"group": lambda s, i: ""})()).group(1)
    m_id = re.search(r"sctidcam=([^&\"<]+)", link)
    camid = (m_id.group(1) if m_id else str(n_cat)).replace(".gif", "").replace(".jpg", "")
    n_cat += 1
    add({
        "key": "cat-" + camid, "prefix": "cat",
        "project_name": f"{road} km {pk} ({mun})".replace("()", ""),
        "url": "https://transit.gencat.cat/ca/informacio-viaria/estat-transit/cameres-transit/",
        "image_url": link.replace("http://", "https://"),
        "type": "image", "category": "traffic", "country": "Spain",
        "region": "Catalunya", "city": mun, "road": road,
        "lat": lat, "lon": lon, "geo_source": "src:gencat-wfs",
        "location_precision": "precise",
        "live_status": "", "http_status": "", "content_type": "", "last_modified": "",
        "notes": f"source=gencat-wfs-cameres; font={font}; camId={camid}; pk={pk}",
    })
report.append(f"Catalonia: {n_cat}")

# ============ 5) Andorra ============
aj = jload("_es_andorra_api.json")["result"]
n_ando = 0
for c in aj:
    img = c["url_gif"].split("?")[0]
    n_ando += 1
    add({
        "key": f"ando-{c['id']}", "prefix": "ando",
        "project_name": c["title"],
        "url": "https://www.mobilitat.ad/totes-les-cameres",
        "image_url": img, "type": "image", "category": "traffic", "country": "Andorra",
        "region": "", "city": "", "road": c["title"].split("/")[0].strip(),
        "lat": fnum(c.get("lat")), "lon": fnum(c.get("lng")),
        "geo_source": "src:mobilitat.ad-api", "location_precision": "precise",
        "live_status": "", "http_status": "", "content_type": "", "last_modified": "",
        "notes": f"source=mobilitat-ad-api-v1-cameras; camId={c['id']}; catId={c.get('category_id')}",
    })
report.append(f"Andorra: {n_ando}")

# ============ 6) Cantur ============
cj = jload("_es_cantur_pages.json")
n_cnt = 0
for slug, v in cj.items():
    imgs = v.get("imgs") or []
    if not imgs:
        continue
    n_cnt += 1
    add({
        "key": "cnt-" + slug, "prefix": "cnt",
        "project_name": v.get("title") or slug,
        "url": f"https://cantur.com/webcam/{slug}/",
        "image_url": imgs[0], "type": "image", "category": "scenic", "country": "Spain",
        "region": "Cantabria", "city": "", "road": "",
        "lat": None, "lon": None, "geo_source": "nominatim", "location_precision": "",
        "live_status": "", "http_status": "", "content_type": "", "last_modified": "",
        "notes": f"source=cantur-webcams; slug={slug}; category-pending-image-check",
    })
report.append(f"Cantur: {n_cnt}")

# ============ 7) camarasdgt YouTube webcams (alive only) ============
yt = jload("_es_webcam_yt_ids.json")
ya = jload("_es_yt_analysis.json") if os.path.exists(os.path.join(ROOT, "_es_yt_analysis.json")) else {}
n_yt = 0
for vid, meta in yt.items():
    a = ya.get(vid, {})
    oembed_ok = "yt_title" in a
    if not oembed_ok:
        continue  # deleted video (e.g. zurriola 404)
    n_yt += 1
    page = (meta.get("pages") or [""])[0]
    label = (meta.get("labels") or [""])[0]
    is_live = bool(a.get("isLiveNow") or a.get("isLive"))
    add({
        "key": f"ytw-{vid}", "prefix": "web",
        "project_name": a.get("yt_title") or label,
        "url": page,
        "image_url": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
        "type": "youtube", "category": "beach", "country": "Spain",
        "region": "Alicante", "city": "Altea" if "altea" in page else ("Benidorm" if "benidorm" in page else ""),
        "road": "",
        "lat": None, "lon": None,
        "geo_source": "nominatim", "location_precision": "",
        "live_status": "live" if is_live else "",
        "http_status": "", "content_type": "video/youtube", "last_modified": "",
        "stream_url": f"https://www.youtube.com/watch?v={vid}",
        "notes": ("source=camarasdgt-webcam-subtree; ytChannel=" + (a.get("author") or "")
                  + "; channelId=" + (a.get("channel_id") or "")
                  + "; isLiveNow=" + str(is_live)
                  + ("; ytStart=" + str(a.get("startTimestamp") or "") if a.get("startTimestamp") else "")),
    })
report.append(f"YouTube webcams: {n_yt}")

# ============ dedupe vs existing CSV URLs ============
import csv as _csv
_csv.field_size_limit(10**7)
needles = ["trafikoa.eus/static/files/tr/camaras", "vitoria-gasteiz.org/c11-01w/cameras",
           "mct.gencat.cat/mct2bo", "imgs.mobilitat.ad", "cantur.com/camaras",
           "youtube.com/watch?v=hvsK8Fvz4rE", "youtube.com/watch?v=ngOvyL2KbuA",
           "i.ytimg.com/vi/hvsK8Fvz4rE", "i.ytimg.com/vi/ngOvyL2KbuA"]
present = set()
with open(CSV, encoding="utf-8", newline="") as f:
    for r in _csv.DictReader(f):
        u = (r.get("live_stream_url") or "") + " " + (r.get("url") or "")
        for n in needles:
            if n in u:
                present.add(n)
report.append(f"CSV already contains source urls for needles: {sorted(present)}")

# dedupe within inventory: identical image_url
seen_img = {}
kept = []
dupes = []
for e in inv:
    u = e["image_url"]
    if u in seen_img:
        dupes.append((e["key"], seen_img[u]))
        continue
    seen_img[u] = e["key"]
    kept.append(e)
report.append(f"duplicate image_urls within inventory: {len(dupes)} {dupes[:6]}")

# geo validation summary
bad = [e["key"] for e in kept if (e.get("lat") is None and e["prefix"] not in ("web", "cnt"))]
report.append(f"entries without lat/lon: {len(bad)} -> {bad[:12]}")

# cross-provider proximity check (same coords rounded 4dp)
bycoord = {}
for e in kept:
    if e.get("lat") is None:
        continue
    k = (round(e["lat"], 4), round(e["lon"], 4))
    bycoord.setdefault(k, []).append(e["key"])
co = {k: v for k, v in bycoord.items() if len(v) > 1}
report.append(f"identical-coord clusters (>=2 entries): {len(co)}")
for k, v in list(co.items())[:8]:
    report.append(f"  {k}: {v}")

json.dump(kept, open(os.path.join(ROOT, "_es_inventory.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n".join(report))
print("\nTOTAL inventory entries:", len(kept))
from collections import Counter
print("by prefix:", dict(Counter(e["prefix"] for e in kept)))
