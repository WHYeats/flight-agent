import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from serpapi import GoogleSearch
import mcp_server.state as state
from config.settings import SERPAPI_KEY

DEBUG_DIR = os.path.join(os.path.dirname(__file__), "../../debug")


def get_booking_options(flight_key: str | int) -> list[dict] | dict:
    """
    Retrieve booking options for a selected flight from SerpAPI.

    Call this after the user has chosen a specific flight and wants to book it.
    Looks up the flight via token_map → uid → _uid_index to get the booking token
    and required search context (origin, destination, date).

    Args:
        flight_key: The id (int) from flight_results for a single-day search,
                    or the date string (e.g. "2026-06-30") from days_results
                    for a multi-day search.

    Returns:
        {"error": "msg"} — token not found, or API/network error.
        list[dict]       — booking options sorted by airline-first then price, each with:
            book_with:        Seller name (e.g. "Asiana Airlines", "Expedia")
            is_airline:       True if booking directly with the airline
            price:            Price in USD
            fare_class:       Fare tier (e.g. "Economy", "Basic Economy")
            baggage:          List of baggage policy strings
            fare_rules:       List of fare condition strings (refunds, changes, etc.)
            separate_tickets: True if legs must be booked separately
            booking_request:  {"url": "...", "post_data": "..."}
                              Use HTTP POST to url with post_data as raw body.
                              If post_data is absent, use HTTP GET to url directly.

    --- Instructions for the LLM ---

    - Call this when the user says they want to book a specific flight.
    - Pass flight_key as an int id (single-day) or date string (multi-day).
    - Present options to the user: show seller, price, fare class, and baggage policy.
    - Recommend booking directly with the airline (is_airline=True) when available.
    - If separate_tickets=True, warn the user that legs are booked separately.
    - Show the user the booking_request.url and tell them to open it in a browser to complete booking.
    - If error mentions expired token, ask user to search again.
    """
    # ── Step 1: Resolve key → uid → flight context ────────────────────────
    key: str | int = flight_key
    if isinstance(flight_key, str) and flight_key.isdigit():
        key = int(flight_key)

    uid = state.token_map.get(key)
    if uid is None:
        return {"error": f"No flight found for '{flight_key}'. Please search for flights first."}

    context = state._uid_index.get(uid)
    if not context:
        return {"error": f"Flight data not found for uid={uid}. Please search for flights again."}

    flight = context["flight"]
    token = flight.get("booking_token") or flight.get("departure_token", "")
    if not token:
        return {"error": "No booking token available for this flight. Please search for flights again."}

    # ── Step 2: Call SerpAPI with all required params ─────────────────────
    params = {
        "engine": "google_flights",
        "booking_token": token,
        "departure_id": ",".join(context["origin_airports"]),
        "arrival_id": ",".join(context["destination_airports"]),
        "outbound_date": context["date"],
        "type": "2",
        "currency": "USD",
        "api_key": SERPAPI_KEY,
    }
    debug_path = os.path.join(DEBUG_DIR, "booking_query_params.json")
    with open(debug_path, "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in params.items() if k != "api_key"}, f, indent=2)

    try:
        results = GoogleSearch(params).get_dict()
    except Exception as e:
        return {"error": f"Connection error while fetching booking options: {e}"}

    if "error" in results:
        return {"error": f"SerpAPI error: {results['error']}"}

    booking_options = results.get("booking_options", [])
    if not booking_options:
        return {"error": "No booking options returned. The booking token may have expired. "
                         "Please search for flights again."}

    # ── Step 3: Distill booking options ───────────────────────────────────
    output = []
    for option in booking_options:
        separate = option.get("separate_tickets", False)
        together = option.get("together", {})
        booking_request = together.get("booking_request", {})

        output.append({
            "book_with": together.get("book_with", ""),
            "is_airline": together.get("airline", False),
            "price": together.get("price"),
            "fare_class": together.get("option_title", ""),
            "baggage": together.get("baggage_prices", []),
            "fare_rules": together.get("extensions", []),
            "separate_tickets": separate,
            "booking_request": {
                "url": booking_request.get("url", ""),
                "post_data": booking_request.get("post_data", ""),
            },
        })

    # Sort: direct airline options first, then by price
    output.sort(key=lambda x: (not x["is_airline"], x["price"] or float("inf")))

    return output
