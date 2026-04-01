#!/usr/bin/env python3
"""Calculate median from a file containing one number per line."""
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print("Usage: calculate_median.py <file>", file=sys.stderr)
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    with open(file_path) as f:
        values = [float(line.strip()) for line in f if line.strip()]

    if not values:
        print("Error: No values found in file", file=sys.stderr)
        sys.exit(1)

    values.sort()
    n = len(values)
    median = values[n // 2] if n % 2 else (values[n // 2 - 1] + values[n // 2]) / 2
    print(median)


if __name__ == "__main__":
    main()
