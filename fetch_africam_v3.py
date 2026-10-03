#!/usr/bin/env python3
"""V3: Final cleaner - rank live stream candidates by score, manually fix the known cases."""
import json

# Load the v2 debug output
with open("C:/Users/eli6-admin/Documents/eli6-surveillance/africam_full.json") as f:
    full = json.load(f)
with open("C:/Users/eli6-admin/Documents/eli6-surveillance/africam_results.json") as f:
    results = json.load(f)

# Manual corrections (the 13 problematic ones)
# Format: slug -> (yt_id, yt_title)
MANUAL_FIX = {
    "hesc": ("YhXWGJQtEQY", "24/7 Live: Rhino Orphans at HESC | Watch Endangered Rhinos Up Close!"),
    "lesser-flamingos": ("IdDorfgnATw", "Kamfers Dam | Flamingos, Birds & Wildlife 24/7"),
    "senyati": ("EdDdTrahHjI", "Senyati Waterhole LIVE | Elephants & Wildlife in Botswana"),
    "kalahari": ("ZVRUiKmCs84", "Kalahari Salt Pan | Conservation Live Cam"),
    "twin-pan": ("2EZavJUNdLI", "Twin Pan Live Hide Cam | Zarafa Camp | Selinda Reserve, Botswana"),
    "thebasin-selinda": ("vEEGzyCvL8Q", "The Basin Live Hide Cam | By Selinda Camp | Botswana"),
    "jackscamp": ("jG0uYl5S44E", "Live from Jack's Camp | Kalahari Waterhole Cam - Elephants, Lions & More"),
    "camelthorn": ("mk02pEy3FdA", "Camelthorn Waterhole Live - Zebra Migration, Hippos & More | Botswana"),
    "moela": ("54Y7xlLrkuo", "Moela Safari Lodge LIVE - Zebra Migration | Boteti River, Botswana"),
    "ulusaba": ("zqc0Z2oWmo8", "Ulusaba Live Wildlife Camera | Sabi Sand, South Africa"),
    "tembe-elephant-park": ("gdrNUUf-cQw", "Tembe Elephant Park | Wildlife Live Stream"),
    "tau-game-lodge": ("8J9USywkGmw", "Tau Game Lodge | Wildlife Live Stream - Madikwe"),
    "kwa-maritane": ("aWglOXp5id0", "Africam - Kwa Maritane"),
    "founders-lodge-by-mantis": ("LaicUirnDJ4", "Founders Lodge By Mantis | Wildlife Live Stream"),
}

# Kruger Shalati: the actual live cam = 0mmIsIZXJx4 (Bridge View, LIVE Wildlife Stream)
# But "Kruger Shalati | Skukuza" (oeHJXG9mMrI) and "Shalati Sunrise" (eTZ6ZgI8oG0) are also cams
# Bridge View is the most recent main cam.
# No fix needed for v2 result.

# Apply fixes
for r in results:
    slug = r["lodge_slug"]
    if slug in MANUAL_FIX:
        r["yt_id"], r["yt_title"] = MANUAL_FIX[slug]

# Print final
print("=== FINAL CLEAN RESULTS ===\n")
for r in results:
    ok = "OK" if r["yt_id"] else "MISSING"
    print(f"[{ok}] {r['name']:<35} {r['yt_id']:<12} | {r['yt_title']}")
    if r.get("secondary_cams"):
        for s in r["secondary_cams"]:
            print(f"        + secondary: {s.get('yt_id', '?')} -> {s.get('title', '?')}")

# Save
with open("C:/Users/eli6-admin/Documents/eli6-surveillance/africam_results.json", "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

# Build the final structured output the user wants
final = []
# Add 9 already-known Kenya entries
KENYA = [
    ("ol-donyo-lodge", "ol Donyo Lodge (Chyulu Hills)", "XsOU8JnEpNM", "ol Donyo Lodge Live | Chyulu Hills", "Kenya", "Chyulu Hills", -2.683, 37.85),
    ("angama-amboseli", "Angama Amboseli", "i12eS_2YV-s", "Angama Amboseli Live", "Kenya", "Amboseli", -2.65, 37.27),
    ("porini", "Porini Rhino Camp (Ol Pejeta)", "5dhmXmUD1ZE", "Porini Rhino Camp Live | Ol Pejeta", "Kenya", "Ol Pejeta", 0.0, 36.93),
    ("angamamara", "Angama Mara", "Njur5IV7icE", "Angama Mara Live", "Kenya", "Maasai Mara", -1.45, 35.0),
    ("marariver", "Mara River Fig Tree", "ACc7IkdOF-Y", "Mara River Fig Tree Crossing", "Kenya", "Mara Triangle", -1.4, 35.0),
    ("marariver-main", "Mara River Main Crossing", "BaEFc79IMCA", "Mara River Main Crossing", "Kenya", "Mara Triangle", -1.4, 35.0),
    ("tortilis", "Tortilis Camp (Amboseli)", "XyPU5-pNg5E", "Tortilis Camp Amboseli Live", "Kenya", "Amboseli", -2.7, 37.25),
    ("mahali-mzuri-waterhole", "Mahali Mzuri Waterhole", "ZWhvO6R37ck", "Mahali Mzuri Waterhole Live", "Kenya", "Maasai Mara", -1.3, 35.2),
    ("mahali-mzuri-landscape", "Mahali Mzuri Landscape", "jIh2FYqMOw0", "Mahali Mzuri Landscape Live", "Kenya", "Maasai Mara", -1.3, 35.2),
    ("finch-hattons", "Finch Hattons (Tsavo West)", "Xe9CPAdyAro", "Finch Hattons Live", "Kenya", "Tsavo West", -3.0, 38.0),
    ("lentorre-lodge", "Lentorre Lodge (Rift Valley)", "bEmFpjwMOvs", "Lentorre Lodge Live", "Kenya", "South Central Rift Valley", -0.7, 36.0),
]
for slug, name, yid, title, country, region, lat, lng in KENYA:
    final.append({"lodge": slug, "name": name, "yt_id": yid, "yt_title": title, "country": country, "region": region, "lat": lat, "lng": lng})

for r in results:
    final.append({
        "lodge": r["lodge_slug"],
        "name": r["name"],
        "yt_id": r["yt_id"],
        "yt_title": r["yt_title"],
        "country": r["country"],
        "region": r["region"],
        "lat": r["lat"],
        "lng": r["lng"],
        "secondary_cams": r.get("secondary_cams", []),
    })

# Save final combined
with open("C:/Users/eli6-admin/Documents/eli6-surveillance/africam_all_lodges.json", "w") as f:
    json.dump(final, f, indent=2, ensure_ascii=False)

print(f"\n\nTotal: {len(final)} lodges written to africam_all_lodges.json")
