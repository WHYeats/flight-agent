import asyncio
import json
import sys
import os
from datetime import datetime

DEBUG_DIR = os.path.join(os.path.dirname(__file__), "../../debug")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

import mcp_server.state as state
from mcp_server.tools.flexible_dates import _resolve_date, expand_dates
from mcp_server.tools.search_flights import (
    _build_params, _call_api, _parse_window, _time_to_minutes,
)

CACHE_TTL_MINUTES = 30


# ─────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────

def _is_expired(entry: dict) -> bool:
    created_at = entry.get("created_at")
    if not created_at:
        return True
    return (datetime.now() - created_at).total_seconds() > CACHE_TTL_MINUTES * 60


def _extract_time(dt_str: str) -> str:
    """Extract HH:MM from SerpAPI datetime '2026-06-30 10:30', or return as-is."""
    if dt_str and " " in dt_str:
        return dt_str.split(" ")[-1]
    return dt_str


def _filter_raw(
    best_raw: list,
    other_raw: list,
    depart_range: tuple | None,
    arrive_range: tuple | None,
) -> list[tuple]:
    """
    Apply time window prefilter then price/duration/stops thresholds.
    Returns list of (raw_flight_dict, is_best) tuples.
    """
    def passes_time(flight):
        segments = flight.get("flights", [])
        if depart_range and segments:
            t = _time_to_minutes(_extract_time(
                segments[0].get("departure_airport", {}).get("time", "")))
            if t is None or not (depart_range[0] <= t <= depart_range[1]):
                return False
        if arrive_range and segments:
            t = _time_to_minutes(_extract_time(
                segments[-1].get("arrival_airport", {}).get("time", "")))
            if t is None or not (arrive_range[0] <= t <= arrive_range[1]):
                return False
        return True

    best_raw = [f for f in best_raw if passes_time(f)]
    other_raw = [f for f in other_raw if passes_time(f)]

    if not best_raw and not other_raw:
        return []

    best_prices = [f.get("price", 0) for f in best_raw if f.get("price")]
    best_durations = [f.get("total_duration", 0) for f in best_raw if f.get("total_duration")]
    best_stops = [len(f.get("flights", [])) - 1 for f in best_raw]

    price_threshold = min(best_prices) * 1.5 if best_prices else float("inf")
    nonstop_price_threshold = min(best_prices) * 2.5 if best_prices else float("inf")
    duration_threshold = min(best_durations) * 2 if best_durations else float("inf")
    stops_threshold = min(best_stops) if best_stops else float("inf")

    all_raw = best_raw + other_raw
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
                if price and price > nonstop_price_threshold and nonstop_kept:
                    continue
            else:
                if price and price > price_threshold:
                    continue

        if is_nonstop:
            nonstop_kept = True
        kept.append((flight, is_best))

    return kept


def _distill_one(
    flight: dict,
    fid: int,
    is_best: bool,
    min_price: int,
    min_duration: int,
) -> dict:
    """Convert one raw flight into the compact format sent to LLM."""
    segments = flight.get("flights", [])
    layovers = flight.get("layovers", [])
    price = flight.get("price", 0)
    total_duration = flight.get("total_duration", 0)
    stops = len(segments) - 1

    airlines = list(dict.fromkeys(seg.get("airline", "") for seg in segments))
    flight_numbers = ", ".join(
        seg.get("flight_number", "") for seg in segments if seg.get("flight_number")
    )

    # Schedule: "10:30-12:45, 21:20-16:50"
    schedule_parts = []
    for seg in segments:
        dep = _extract_time(seg.get("departure_airport", {}).get("time", ""))
        arr = _extract_time(seg.get("arrival_airport", {}).get("time", ""))
        schedule_parts.append(f"{dep}-{arr}")
    schedule = ", ".join(schedule_parts)

    # Transit summary
    if stops == 0:
        transit = "nonstop"
    else:
        stop_names = [lv.get("name", lv.get("id", "")) for lv in layovers]
        transit = f"{stops} stop{'s' if stops > 1 else ''} at {', '.join(stop_names)}"

    # Tags / notices
    tags = []
    if stops == 0:
        tags.append("direct flight")
    if is_best:
        tags.append("best choice")
    if not price:
        tags.append("price unavailable")
    if price and price == min_price:
        tags.append("least price")
    if total_duration and total_duration == min_duration:
        tags.append("least total duration")
    for lv in layovers:
        if lv.get("duration", 999) < 90:
            tags.append("tight connection")
            break
    for lv in layovers:
        if lv.get("overnight"):
            tags.append("overnight layover")
            break
    for i in range(len(segments) - 1):
        arr_id = segments[i].get("arrival_airport", {}).get("id", "")
        dep_id = segments[i + 1].get("departure_airport", {}).get("id", "")
        if arr_id and dep_id and arr_id != dep_id:
            tags.append(f"airport change ({arr_id}→{dep_id})")
            break

    return {
        "id": fid,
        "airline": " / ".join(airlines),
        "price": f"${price}" if price else "N/A",
        "flights": flight_numbers,
        "schedule": schedule,
        "transit": transit,
        "tags": tags,
    }


def _distill_flights_result(flights_with_uid: list[dict]) -> list[dict]:
    """
    Distill all flights for a single day into flight_results.
    Assigns sequential IDs starting from 1, rebuilds state.token_map as {id: uid}.
    """
    all_prices = [e["flight"].get("price", 0) for e in flights_with_uid]
    all_durations = [e["flight"].get("total_duration", 0) for e in flights_with_uid]
    min_price = min((p for p in all_prices if p), default=0)
    min_duration = min((d for d in all_durations if d), default=0)

    new_token_map = {}
    results = []
    for fid, entry in enumerate(flights_with_uid, start=1):
        new_token_map[fid] = entry["uid"]
        results.append(_distill_one(entry["flight"], fid, entry["is_best"], min_price, min_duration))

    state.token_map = new_token_map
    return results


def _distill_days_result(dates: list[str]) -> dict:
    """
    Distill one best flight per day into days_results.
    Assigns sequential IDs across dates, rebuilds state.token_map as {date: token}.
    """
    # Global min price across all days for "least price" tag
    all_day_prices = []
    all_day_durations = []
    for date in dates:
        entry = state._flight_store.get(date, {})
        for e in entry.get("flights", []):
            flight = e["flight"]
            if flight.get("price"):
                all_day_prices.append(flight["price"])
            if flight.get("total_duration"):
                all_day_durations.append(flight["total_duration"])
    global_min_price = min(all_day_prices, default=0)
    global_min_duration = min(all_day_durations, default=0)

    new_token_map = {}
    days_result = {}
    fid = 1

    for date in dates:
        store_entry = state._flight_store.get(date)
        if not store_entry or not store_entry.get("flights"):
            continue

        flights_with_uid = store_entry["flights"]
        # Pick best: first with is_best=True, else first overall
        best_entry = next(
            (e for e in flights_with_uid if e["is_best"]),
            flights_with_uid[0],
        )
        new_token_map[date] = best_entry["uid"]
        days_result[date] = _distill_one(
            best_entry["flight"], fid, best_entry["is_best"],
            global_min_price, global_min_duration,
        )
        fid += 1

    state.token_map = new_token_map
    return days_result


# ─────────────────────────────────────────────
# Main MCP tool
# ─────────────────────────────────────────────

async def search_flight_workflow(
    origin_airports: list[str],
    destination_airports: list[str],
    date_from: str,
    date_to: str = "",
    buffer_days: int = 0,
    travel_class: int = 1,
    include_airlines: list[str] = [],
    exclude_airlines: list[str] = [],
    max_stops: int = -1,
    max_price: int = -1,
    depart_window: str = "",
    arrive_window: str = "",
) -> list | dict:
    """
    Search for one-way flights across one or multiple dates. Combines date expansion,
    parallel API calls, caching, filtering, and result distillation into one tool.

    Args:
        origin_airports:      IATA codes for departure (e.g. ["DLC"]).
        destination_airports: IATA codes for arrival (e.g. ["LAX", "BUR"]).
        date_from:            Departure date or range start in MM-DD or YYYY-MM-DD.
                              Year is inferred automatically if omitted.
        date_to:              Range end date (MM-DD or YYYY-MM-DD). Use for date ranges.
        buffer_days:          Days around date_from to search (e.g. 2 → ±2 days).
                              Use when user says "around" or "roughly".
        travel_class:         1=economy (default), 2=premium economy, 3=business, 4=first.
        include_airlines:     IATA codes to include (e.g. ["NH","JL"]).
                              Cannot be combined with exclude_airlines.
        exclude_airlines:     IATA codes to exclude. Cannot be combined with include_airlines.
        max_stops:            0=nonstop, 1=1 stop, -1=no limit. Sent to SerpAPI.
        max_price:            Max price in USD. -1=no limit.
        depart_window:        Departure time window "HH:MM-HH:MM". Empty=no constraint.
        arrive_window:        Arrival time window "HH:MM-HH:MM". Empty=no constraint.

    Returns:
        {"error": "msg"}  — API/network error, relay to user.
        []                — No flights found, suggest relaxing constraints.

        Single date → flight_results (list):
            Each item: {id, airline, price, flights, schedule, transit, tags}
            User selects by id: "I want option 2".
            Call get_booking_link with id=2 to get the booking URL.

        Multiple dates → days_results (dict keyed by date):
            Each date: {id, airline, price, flights, schedule, transit, tags}
            User selects by date: "I'll go on June 30th".
            Call get_booking_link with date="2026-06-30" to get the booking URL.
            User can also say "show me all flights on June 30th" — call this tool
            again with only date_from="2026-06-30" (cache will be used if not expired).

    --- Instructions for the LLM ---

    - Always use this tool for flight search. Do not call expand_dates or search_flights separately.
    - resolve_airports must be called first to get airport codes.
    - Single exact date: set only date_from (e.g. date_from="06-30").
    - Date range: set date_from and date_to (e.g. "06-28" to "07-02").
    - Flexible dates: set date_from and buffer_days (e.g. "around June 30" → buffer_days=2).
    - Map user constraints:
        "nonstop"             → max_stops=0
        "after 10 AM"         → depart_window="10:00-23:59"
        "arrive before 6 PM"  → arrive_window="00:00-18:00"
        "budget under $800"   → max_price=800
        "business class"      → travel_class=3
        "avoid United"        → exclude_airlines=["UA"]
    - If [] returned, suggest relaxing constraints (budget, stops, time window).
    - Always show the id number for each flight option in your response (e.g. "[1] UA 923").
      Users refer to flights by id or flight number — map flight number back to id when needed.
    - For single-day results: user books by id ("I want option 2" or "I want UA 923" → id=1).
    - For multi-day results: show price/schedule per date and ask which date or if they want
      to see all flights on a specific date. User books by date ("I'll go June 30th").
    """
    # ── Step 1: Expand dates ──────────────────────────────────────────────
    if date_to or buffer_days:
        dates = expand_dates(date_from, date_to, buffer_days)
    else:
        resolved = _resolve_date(date_from)
        dates = [resolved.isoformat()] if resolved else []

    if not dates:
        return {"error": "Invalid date input — could not parse the date provided."}

    depart_range = _parse_window(depart_window)
    arrive_range = _parse_window(arrive_window)

    # ── Step 2: Search uncached dates in parallel ─────────────────────────
    async def _search_one(date: str):
        entry = state._flight_store.get(date)
        if entry and not _is_expired(entry):
            return date, None  # cache hit
        params = _build_params(
            origin_airports, destination_airports, date,
            2, travel_class, include_airlines, exclude_airlines, max_price, max_stops,
        )
        debug_path = os.path.join(DEBUG_DIR, f"search_params_{date}.json")
        with open(debug_path, "w", encoding="utf-8") as f:
            json.dump({k: v for k, v in params.items() if k != "api_key"}, f, indent=2)

        result = await asyncio.to_thread(_call_api, params)
        return date, result

    api_results = await asyncio.gather(*[_search_one(d) for d in dates])

    # ── Step 3: Filter and store ──────────────────────────────────────────
    errors = []
    for date, result in api_results:
        if result is None:
            continue  # cache hit, keep existing entry
        if isinstance(result, dict):
            errors.append(f"{date}: {result['error']}")
            continue
        best_raw, other_raw = result
        # Save raw API result for debugging
        raw_path = os.path.join(DEBUG_DIR, f"raw_{date}.json")
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump({"best_flights": best_raw, "other_flights": other_raw}, f, indent=2, ensure_ascii=False)

        kept = _filter_raw(best_raw, other_raw, depart_range, arrive_range)
        min_price = min((f.get("price", 0) for f, _ in kept if f.get("price")), default=0)

        # Assign uids and register in _uid_index
        flights_with_uid = []
        for flight, is_best in kept:
            uid = state._next_uid
            state._next_uid += 1
            state._uid_index[uid] = {
                "flight": flight,
                "date": date,
                "origin_airports": origin_airports,
                "destination_airports": destination_airports,
            }
            flights_with_uid.append({"flight": flight, "is_best": is_best, "uid": uid})

        state._flight_store[date] = {
            "min_price": min_price,
            "created_at": datetime.now(),
            "flights": flights_with_uid,
        }

    # If all dates errored and nothing is cached, return the error
    valid_dates = [d for d in dates if state._flight_store.get(d) and state._flight_store[d].get("flights")]
    if not valid_dates:
        if errors:
            return {"error": "; ".join(errors)}
        return []

    # ── Step 4: Distill and return ────────────────────────────────────────
    if len(dates) == 1:
        entry = state._flight_store[valid_dates[0]]
        result = _distill_flights_result(entry["flights"])
        distilled_path = os.path.join(DEBUG_DIR, f"distilled_{valid_dates[0]}.json")
        with open(distilled_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        return result
    else:
        result = _distill_days_result(valid_dates)
        distilled_path = os.path.join(DEBUG_DIR, "distilled_days.json")
        with open(distilled_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        return result
