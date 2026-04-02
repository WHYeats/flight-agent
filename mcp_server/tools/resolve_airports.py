import csv
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from data.city_airport_map import CITY_AIRPORT_MAP

_AIRPORTS_CSV = os.path.join(os.path.dirname(__file__), "../../data/airports_iata.csv")

# Load CSV once at import time
_airports: list[dict] = []
with open(_AIRPORTS_CSV, newline="", encoding="utf-8") as f:
    _airports = list(csv.DictReader(f))


def resolve_airports(city: str, iso_country: str, iso_region: str = "") -> list[str]:
    """
    Given a city name and ISO country code, return IATA codes of major commercial airports.

    Args:
        city:        City or metro area name (e.g. "Tokyo", "Los Angeles"). Case-insensitive.
        iso_country: 2-letter ISO 3166-1 country code (e.g. "US", "GB", "JP").
                     You MUST determine this from context before calling.
        iso_region:  Optional ISO 3166-2 region/state code (e.g. "US-CA", "GB-ENG").
                     Provide this when the city name is ambiguous within a country
                     (e.g. "Portland" exists in both US-OR and US-ME).

    Returns:
        List of IATA codes. Empty list if nothing found.

    --- Instructions for the LLM calling this tool ---

    SKIP this function entirely if the user has already provided explicit IATA airport
    codes (e.g. "Tokyo (HND and NRT)", "fly out of LAX"). In that case, use the codes
    directly without calling this function.

    Otherwise, determine iso_country using your world knowledge before calling:

    (a) If the city name unambiguously refers to one dominant city worldwide
        (e.g. "Tokyo" -> JP, "London" -> GB, "Los Angeles" -> US), infer iso_country
        directly and call this function without asking the user.

    (b) If the city name is shared by multiple notable cities across countries
        (e.g. "San Jose" -> US or CR, "Portland" -> US-OR or US-ME,
        "Victoria" -> CA, AU, or SC), ask the user to clarify which city they mean
        before calling this function.

    (c) If the user has already specified the country or region in their query
        (e.g. "London, Ontario" or "San Jose, Costa Rica"), use that directly.

    Examples:
        resolve_airports("Tokyo", "JP")           -> ["HND", "NRT"]
        resolve_airports("Los Angeles", "US")     -> ["LAX", "BUR", "SNA", "ONT", "LGB"]
        resolve_airports("Las Vegas", "US")       -> ["LAS"]
        resolve_airports("London", "GB")          -> ["LHR", "LGW", "STN", "LTN", "LCY", "SEN"]
        resolve_airports("London", "CA")          -> airports near London, Ontario
    """
    city_lower = city.strip().lower()
    country_upper = iso_country.strip().upper()

    # Step 1: check static map — requires exact city + country match
    key = (city_lower, country_upper)
    if key in CITY_AIRPORT_MAP:
        return CITY_AIRPORT_MAP[key]

    # Step 2: fall back to CSV — match municipality + country, optionally region
    matches = []
    for row in _airports:
        iata = row.get("iata_code", "").strip()
        if not iata:
            continue

        row_country = row.get("iso_country", "").strip().upper()
        if row_country != country_upper:
            continue

        # If iso_region provided, filter by region too
        if iso_region:
            row_region = row.get("iso_region", "").strip().upper()
            if row_region != iso_region.strip().upper():
                continue

        municipality = row.get("municipality", "").strip().lower()
        keywords = row.get("keywords", "").strip().lower()

        if city_lower == municipality or city_lower in keywords:
            matches.append(iata)

    return matches
