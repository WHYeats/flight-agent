import sys
import os
from serpapi import GoogleSearch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from config.settings import SERPAPI_KEY


# ─────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────

def _format_duration(minutes: int) -> str:
    """Convert minutes to human-readable string, e.g. 645 -> '10h 45m'."""
    if not minutes:
        return "N/A"
    h, m = divmod(int(minutes), 60)
    return f"{h}h {m}m" if h else f"{m}m"


def _parse_window(window: str) -> tuple[int, int] | None:
    """
    Parse a time window string 'HH:MM-HH:MM' into (start_minutes, end_minutes).
    Returns None if window is empty or malformed.
    Example: '08:00-11:59' -> (480, 719)
    """
    if not window:
        return None
    try:
        start_str, end_str = window.split("-", 1)
        sh, sm = start_str.strip().split(":")
        eh, em = end_str.strip().split(":")
        return int(sh) * 60 + int(sm), int(eh) * 60 + int(em)
    except Exception:
        return None


def _time_to_minutes(t: str) -> int | None:
    """
    Parse a time string 'H:MM' or 'HH:MM' into total minutes since midnight.
    Returns None if malformed.
    """
    try:
        h, m = t.strip().split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return None


def _build_itinerary(flight: dict) -> list[dict]:
    """
    Interleave flight segments and layovers into a single itinerary list.

    Output alternates: flight → layover → flight → layover → flight ...
    """
    segments = flight.get("flights", [])
    layovers = flight.get("layovers", [])
    itinerary = []

    for i, seg in enumerate(segments):
        dep = seg.get("departure_airport", {})
        arr = seg.get("arrival_airport", {})

        itinerary.append({
            "type": "flight",
            "from": dep.get("id", ""),
            "to": arr.get("id", ""),
            "time": f"{dep.get('time', '')} - {arr.get('time', '')}",
            "duration": _format_duration(seg.get("duration")),
            "flight_number": seg.get("flight_number", ""),
            "airline": seg.get("airline", ""),
            "airplane": seg.get("airplane", ""),
        })

        # Insert layover after each segment except the last
        if i < len(layovers):
            lv = layovers[i]
            lv_duration = lv.get("duration", 0)
            lv_entry = {
                "type": "layover",
                "location": lv.get("name", ""),
                "duration": _format_duration(lv_duration),
            }
            # Add warnings
            warnings = []
            if lv_duration and lv_duration < 90:
                warnings.append("Tight connection")
            if lv.get("overnight"):
                warnings.append("Overnight layover")
            if warnings:
                lv_entry["warning"] = ", ".join(warnings)

            itinerary.append(lv_entry)

    return itinerary


# ─────────────────────────────────────────────
# Step 1: Build SerpAPI parameters
# ─────────────────────────────────────────────

def _build_params(
    origin_airports: list[str],
    destination_airports: list[str],
    date: str,
    flight_type: int,
    travel_class: int,
    include_airlines: list[str],
    exclude_airlines: list[str],
    max_price: int,
    max_stops: int,
) -> dict:
    params = {
        "engine": "google_flights",
        "departure_id": ",".join(origin_airports),
        "arrival_id": ",".join(destination_airports),
        "outbound_date": date,
        "type": str(flight_type),
        "travel_class": str(travel_class),
        "currency": "USD",
        "api_key": SERPAPI_KEY,
    }
    if max_price > 0:
        params["max_price"] = max_price
    if max_stops >= 0:
        params["stops"] = max_stops
    # include_airlines and exclude_airlines cannot be used together
    if include_airlines:
        params["include_airlines"] = ",".join(include_airlines)
    elif exclude_airlines:
        params["exclude_airlines"] = ",".join(exclude_airlines)

    return params


# ─────────────────────────────────────────────
# Step 2: Call API and return raw flight lists
# ─────────────────────────────────────────────

def _call_api(params: dict) -> tuple[list, list] | dict:
    """
    Call SerpAPI and return (best_flights, other_flights) as raw dicts.
    Returns {"error": "..."} on network failure or API-level error (e.g. invalid key, quota exceeded).
    """
    try:
        results = GoogleSearch(params).get_dict()
    except Exception as e:
        return {"error": f"Connection error while calling SerpAPI: {e}"}

    if "error" in results:
        return {"error": f"SerpAPI error: {results['error']}"}

    return results.get("best_flights", []), results.get("other_flights", [])


# ─────────────────────────────────────────────
# Step 3: Filter, format, and annotate results
# ─────────────────────────────────────────────

def _filter_and_format(best_raw: list, other_raw: list) -> list[dict]:
    """
    Filter other_flights based on best_flights benchmarks, format all kept
    results into the output structure, and annotate with notices.
    """
    if not best_raw and not other_raw:
        return []

    all_raw = best_raw + other_raw
    # Compute benchmarks from best_flights only
    best_prices = [f.get("price", 0) for f in best_raw if f.get("price")]
    best_durations = [f.get("total_duration", 0) for f in best_raw if f.get("total_duration")]
    best_stops = [len(f.get("flights", [])) - 1 for f in best_raw]

    price_threshold = min(best_prices) * 1.5 if best_prices else float("inf")
    nonstop_price_threshold = min(best_prices) * 2.5 if best_prices else float("inf")
    duration_threshold = min(best_durations) * 2 if best_durations else float("inf")
    stops_threshold = min(best_stops) if best_stops else float("inf")

    # Filter: always keep best_flights; apply thresholds to other_flights.
    # Nonstop flights use a relaxed 2.5x price threshold.
    # At least one nonstop is always kept regardless of price.
    kept = []
    nonstop_kept = False
    for i, flight in enumerate(all_raw):
        is_best = i < len(best_raw)
        price = flight.get("price", 0)
        duration = flight.get("total_duration", 0)
        stops = len(flight.get("flights", [])) - 1
        is_nonstop = stops == 0

        if not is_best:
            if duration > duration_threshold:
                continue
            if stops > stops_threshold:
                continue
            if is_nonstop:
                # Always keep the first nonstop found; others need 2.5x threshold
                if price and price > nonstop_price_threshold and nonstop_kept:
                    continue
            else:
                if price and price > price_threshold:
                    continue

        if is_nonstop:
            nonstop_kept = True
        kept.append((flight, is_best))

    if not kept:
        return []

    # Compute global min price and duration across kept results for notices
    all_prices = [f.get("price", 0) for f, _ in kept]
    all_durations = [f.get("total_duration", 0) for f, _ in kept]
    min_price = min(p for p in all_prices if p)
    min_duration = min(d for d in all_durations if d)

    results = []
    for idx, (flight, is_best) in enumerate(kept):
        segments = flight.get("flights", [])
        layovers = flight.get("layovers", [])
        price = flight.get("price", 0)
        total_duration = flight.get("total_duration", 0)
        stops = len(segments) - 1
        airlines = list(dict.fromkeys(seg.get("airline", "") for seg in segments))

        # Build notices
        notices = []
        if is_best:
            notices.append("best choice")
        if not price:
            notices.append("price unavailable")
        if price and price == min_price:
            notices.append("least price")
        if total_duration and total_duration == min_duration:
            notices.append("least total duration")
        if any(lv.get("duration", 999) < 90 for lv in layovers):
            notices.append("tight connection")
        if any(lv.get("overnight") for lv in layovers):
            notices.append("overnight layover")
        # Detect airport change at transit: arrival airport of seg[i] != departure of seg[i+1]
        for i in range(len(segments) - 1):
            arr = segments[i].get("arrival_airport", {}).get("id", "")
            dep = segments[i + 1].get("departure_airport", {}).get("id", "")
            if arr and dep and arr != dep:
                notices.append(f"airport change at transit ({arr} → {dep})")
                break

        booking_token = flight.get("booking_token") or flight.get("departure_token", "")

        results.append({
            "id": idx + 1,
            "airlines": airlines,
            "price": f"${price}" if price else "N/A",
            "total_duration": _format_duration(total_duration),
            "stops": stops,
            "notices": notices,
            "itinerary": _build_itinerary(flight),
            "booking_token": booking_token,
        })

    return results


# ─────────────────────────────────────────────
# Main MCP tool
# ─────────────────────────────────────────────

def search_flights(
    origin_airports: list[str],
    destination_airports: list[str],
    date: str,
    flight_type: int = 2,
    travel_class: int = 1,
    include_airlines: list[str] = [],
    exclude_airlines: list[str] = [],
    max_stops: int = -1,
    max_price: int = -1,
    depart_window: str = "",
    arrive_window: str = "",
) -> list[dict] | dict:
    """
    Search for flights using SerpAPI Google Flights, filter results, and return
    a structured list ready for LLM recommendation.

    Args:
        origin_airports:      List of departure IATA codes (e.g. ["HND", "NRT"]).
        destination_airports: List of arrival IATA codes (e.g. ["LAX", "BUR"]).
        date:                 Departure date in YYYY-MM-DD format.
        flight_type:          1=round-trip, 2=one-way (default), 3=multi-city.
                              Only one-way (2) is fully supported. For other types,
                              this function returns a notice dict immediately.
        travel_class:         1=economy (default), 2=premium economy, 3=business, 4=first.
        include_airlines:     List of 2-letter IATA airline codes to include (e.g. ["UA", "DL"]).
                              Cannot be used together with exclude_airlines.
        exclude_airlines:     List of 2-letter IATA airline codes to exclude.
                              Cannot be used together with include_airlines.
        max_stops:            Maximum stops. -1=no limit, 0=nonstop, 1=one stop, 2=two stops.
                              Sent directly to SerpAPI as the stops parameter.
        max_price:            Maximum price in USD. -1=no limit.
        depart_window:        Departure time window "HH:MM-HH:MM" (24h). Empty = no constraint.
                              E.g. "08:00-11:59" keeps flights departing 08:00–11:59.
        arrive_window:        Arrival time window "HH:MM-HH:MM" (24h). Empty = no constraint.
                              E.g. "12:00-15:59" keeps flights arriving 12:00–15:59.

    Returns:
        {"error": "msg"}: API/network error — relay to user.
        []: No flights found — suggest user relax constraints (budget, stops, time window).
        list[dict]: Results with id, airlines, price, total_duration, stops, notices,
                    itinerary, booking_token. booking_token can be passed to get_booking_link.

    --- Instructions for the LLM ---

    - Only flight_type=2 (one-way) is supported. Do not call with 1 or 3 — instead tell
      the user that round-trip and multi-city are not yet supported.
    - Call once per date. If expand_dates returned N dates, call this tool N times.
    - Pass airport code lists from resolve_airports directly.
    - Map user constraints to parameters:
        stops/price/class: max_stops=0 (nonstop), max_price=800, travel_class=3 (business)
        airlines: include_airlines=["NH","JL"] or exclude_airlines=["UA"]
        time: depart/arrive windows in "HH:MM-HH:MM"; interpret naturally:
              "after 10 AM" -> "10:00-23:59", "morning arrival" -> "00:00-11:59",
              "no later than 4 PM" -> "00:00-16:00", "around noon" -> "11:00-13:00"
    - If tool returns [], suggest user relax constraints (e.g. higher budget, flexible time).
    """
    # Guard: only one-way supported
    if flight_type != 2:
        type_name = {1: "round-trip", 3: "multi-city"}.get(flight_type, f"type={flight_type}")
        return {
            "notice": (
                f"This agent currently supports one-way flights only. "
                f"You requested a {type_name} flight. "
                f"Please split your journey into individual one-way searches, "
                f"or let the user know this trip type is not yet supported."
            )
        }

    params = _build_params(
        origin_airports, destination_airports, date,
        flight_type, travel_class,
        include_airlines, exclude_airlines, max_price, max_stops,
    )

    result = _call_api(params)
    if isinstance(result, dict):
        return result
    best_raw, other_raw = result

    if not best_raw and not other_raw:
        return []

    # Parse time windows once (None if empty/malformed)
    depart_range = _parse_window(depart_window)
    arrive_range = _parse_window(arrive_window)

    # Apply prefilters to raw results before formatting
    def _passes_prefilter(flight: dict) -> bool:
        segments = flight.get("flights", [])
        if depart_range and segments:
            dep_minutes = _time_to_minutes(segments[0].get("departure_airport", {}).get("time", ""))
            if dep_minutes is None or not (depart_range[0] <= dep_minutes <= depart_range[1]):
                return False
        if arrive_range and segments:
            arr_minutes = _time_to_minutes(segments[-1].get("arrival_airport", {}).get("time", ""))
            if arr_minutes is None or not (arrive_range[0] <= arr_minutes <= arrive_range[1]):
                return False
        return True

    best_raw = [f for f in best_raw if _passes_prefilter(f)]
    other_raw = [f for f in other_raw if _passes_prefilter(f)]

    return _filter_and_format(best_raw, other_raw)
