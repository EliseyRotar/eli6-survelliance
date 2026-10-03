#!/usr/bin/env python3
"""
Controllable Webcams CSV/TSV -> URL list extractor.

Reads a Reddit-dump-style file where the last column is `url`. The file is
tab-delimited in your example. Each non-empty URL (or self.controllablewebcams
permalink) is written as a single URL per line.
"""

import argparse
import csv
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract URLs from a controllable webcams dump.")
    parser.add_argument("input", help="Path to the dump file (TSV or CSV)")
    parser.add_argument("-o", "--output", default="-", help="Output file ('-' for stdout)")
    parser.add_argument("--delimiter", default="\t", help="Field delimiter (default: TAB)")
    args = parser.parse_args(argv)

    with open(args.input, "r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter=args.delimiter)
        urls = []
        for row in reader:
            url = (row.get("url") or "").strip()
            if not url:
                continue
            # Skip reddit permalinks (self.controllablewebcams rows).
            if "reddit.com/r/" in url:
                continue
            if url not in urls:
                urls.append(url)

    out = sys.stdout if args.output == "-" else open(args.output, "w", encoding="utf-8")
    try:
        for u in urls:
            out.write(u + "\n")
    finally:
        if out is not sys.stdout:
            out.close()

    if args.output == "-":
        sys.stderr.write(f"# Extracted {len(urls)} URLs\n")
    else:
        print(f"Extracted {len(urls)} URLs -> {args.output}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main() or 0)
