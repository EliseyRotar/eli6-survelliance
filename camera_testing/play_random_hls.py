"""Pick a random m3u8 entry from CSV and launch the HLS player."""
import csv
import random
import subprocess
import sys

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
PLAYER_BAT = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\launch_hls_player.bat'


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None  # optional idx or 'random'

    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))

    # m3u8 in live_stream_url (column 3)
    m3u8_rows = [r for r in rows[1:] if len(r) > 3 and r[3] and '.m3u8' in r[3].lower()]

    if not target or target == 'random':
        chosen = random.choice(m3u8_rows)
    elif target.isdigit():
        idx = int(target)
        chosen = next((r for r in m3u8_rows if r[0] == str(idx)), None)
        if not chosen:
            print(f'idx {idx} not in m3u8 set', file=sys.stderr)
            return
    else:
        # substring match
        chosen = next((r for r in m3u8_rows if target.lower() in r[1].lower() or target.lower() in r[3].lower()), None)
        if not chosen:
            print(f'no match for {target!r}', file=sys.stderr)
            return

    idx, name, url = chosen[0], chosen[1], chosen[3]
    print(f'idx={idx} {name}')
    print(f'url={url}')
    subprocess.run([PLAYER_BAT, url], shell=False)


if __name__ == '__main__':
    main()
