"""
Run this script once after placing airports.csv in the data/ folder.
It removes all airports without an IATA code and saves the result as airports_iata.csv.

Usage:
    python data/prepare_airports.py
"""

import csv
import os

INPUT_FILE = os.path.join(os.path.dirname(__file__), "airports.csv")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "airports_iata.csv")


def prepare():
    with open(INPUT_FILE, newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        _allowed_types = {"large_airport", "medium_airport"}
        rows = [
            row for row in reader
            if row.get("iata_code", "").strip()
            and row.get("type", "").strip() in _allowed_types
            and row.get("scheduled_service", "").strip().lower() == "yes"
            and row.get("icao_code", "").strip()  # ensure ICAO code is present
        ]

    fieldnames = reader.fieldnames
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done. {len(rows)} airports with IATA codes saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    prepare()
