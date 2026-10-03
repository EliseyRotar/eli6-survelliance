#!/usr/bin/env python3

import os
import sys
import subprocess

GLOBAL_DATA = {}

FIELD_ORDER = [
    "con-bounces",
    "contentions",
    "waittime-min",
    "waittime-max",
    "waittime-total",
    "waittime-avg",
    "acq-bounces",
    "acquisitions",
    "holdtime-min",
    "holdtime-max",
    "holdtime-total",
    "holdtime-avg",
]


def do_summarize_file(root, filename):
    full_path = os.path.join(root, filename)

    # Create a non-overwriting summary filename
    summary_filename = f"summary_of_locks.txt"
    summary_path = os.path.join(root, summary_filename)

    print(f"Processing: {full_path}")

    # Use grep directly (no cat)
    cmd = f'grep ":" "{full_path}" | head'

    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )

    # grep returns:
    # 0 = matches found
    # 1 = no matches
    # >1 = actual error
    if result.returncode > 1:
        print(f"Error processing {full_path}: {result.stderr}")
        sys.exit(1)

    with open(summary_path, "w") as f:
        f.write(result.stdout)

def do_collect_summary_data(root, filename):
    global GLOBAL_DATA

    summary_path = os.path.join(root, filename)

    if not os.path.isfile(summary_path):
        raise FileNotFoundError(f"{summary_path} does not exist")

    file_entry = {
        "locks": []
    }

    with open(summary_path, "r") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            parts = line.split()

            if len(parts) < 2:
                continue

            lock_name = parts[0]

            if lock_name.endswith(":"):
                lock_name = lock_name[:-1]

            numeric_values = []

            for field in parts[1:]:
                try:
                    if "." in field:
                        numeric_values.append(float(field))
                    else:
                        numeric_values.append(int(field))
                except ValueError:
                    continue

            file_entry["locks"].append({
                "lock_name": lock_name,
                "values": numeric_values
            })

    GLOBAL_DATA[summary_path] = file_entry


def values_to_dict(values):
    return dict(zip(FIELD_ORDER, values))


def do_merge_lock_data():
    global GLOBAL_DATA

    merged = {}

    for file_path, file_data in GLOBAL_DATA.items():
        for lock_entry in file_data["locks"]:
            name = lock_entry["lock_name"]
            values = lock_entry["values"]

            if len(values) != len(FIELD_ORDER):
                raise ValueError(
                    f"Unexpected column count in {file_path} for lock {name}"
                )

            if name not in merged:
                merged[name] = values_to_dict(values)
                merged[name]["contributors"] = 1
                continue

            m = merged[name]

            # Sums
            m["con-bounces"] += values[0]
            m["contentions"] += values[1]
            m["waittime-total"] += values[4]
            m["acq-bounces"] += values[6]
            m["acquisitions"] += values[7]
            m["holdtime-total"] += values[10]

            # Min / Max
            m["waittime-min"] = min(m["waittime-min"], values[2])
            m["waittime-max"] = max(m["waittime-max"], values[3])
            m["holdtime-min"] = min(m["holdtime-min"], values[8])
            m["holdtime-max"] = max(m["holdtime-max"], values[9])

            m["contributors"] += 1

    # Recompute averages properly
    for name, m in merged.items():
        contentions = m["contentions"]
        acquisitions = m["acquisitions"]

        m["waittime-avg"] = (
            m["waittime-total"] / contentions if contentions > 0 else 0.0
        )

        m["holdtime-avg"] = (
            m["holdtime-total"] / acquisitions if acquisitions > 0 else 0.0
        )

    return merged

def print_report_sorted_by_waittime(merged_data):
    if not merged_data:
        print("No data to report.")
        return

    # Sort locks by waittime-total descending
    sorted_locks = sorted(
        merged_data.items(),
        key=lambda item: item[1]["waittime-total"],
        reverse=True
    )

    # Header
    header = (
        f"{'Lock Name':40} "
        f"{'Wait Total':>15} "
        f"{'Contentions':>12} "
        f"{'Wait Avg':>12} "
        f"{'Wait Max':>12} "
        f"{'Acquisitions':>14}"
    )
    print(header)
    print("-" * len(header))

    for lock_name, stats in sorted_locks:
        print(
            f"{lock_name:40} "
            f"{stats['waittime-total']:15.2f} "
            f"{stats['contentions']:12d} "
            f"{stats['waittime-avg']:12.2f} "
            f"{stats['waittime-max']:12.2f} "
            f"{stats['acquisitions']:14d}"
        )


def do_recurse_tree(start_dir, mode):
    needle = ""
    fptr = None
    if mode == "summarize":
        needle = "lock_stat"
        fptr = do_summarize_file
    elif mode == "collect":
        needle = "summary_of_locks"
        fptr = do_collect_summary_data
    else:
        print(f"Error: bad mode.")
        sys.exit(1)

    for root, dirs, files in os.walk(start_dir):
        for filename in files:
            if needle in filename:
                fptr(root, filename)


def main():
    if len(sys.argv) > 2:
        print(f"Usage: {sys.argv[0]} [start_directory]")
        sys.exit(1)

    start_dir = sys.argv[1] if len(sys.argv) == 2 else os.getcwd()

    if not os.path.isdir(start_dir):
        print(f"Error: '{start_dir}' is not a valid directory.")
        sys.exit(1)

    do_recurse_tree(start_dir, "summarize")
    do_recurse_tree(start_dir, "collect")
    #print(str(GLOBAL_DATA))
    md = do_merge_lock_data()
    print_report_sorted_by_waittime(md)

if __name__ == "__main__":
    main()
