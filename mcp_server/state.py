"""
Shared in-session state for the flight agent MCP server.

_flight_store:
    Maps date string (YYYY-MM-DD) to a dict:
        {
            "min_price": int,
            "created_at": datetime,
            "flights": [{"flight": raw_dict, "is_best": bool, "uid": int}, ...]
        }
    Refreshed on every SerpAPI call. TTL = 30 min.

_uid_index:
    Maps uid (int) to flight context needed for booking:
        {
            "flight": raw_flight_dict,
            "date": "YYYY-MM-DD",
            "origin_airports": ["DLC"],
            "destination_airports": ["LAX", "BUR"],
        }
    Populated when flights are stored. Never cleared — uids are permanent.

_next_uid:
    Monotonically increasing counter for uid assignment.

token_map:
    Rebuilt every time results are sent to LLM. Two modes (never mixed):
        Multi-day:  {"2026-06-30": uid, ...}   keyed by date string
        Single-day: {1: uid, 2: uid, ...}       keyed by int flight id
    Values are uids, not tokens — look up token via _uid_index.

State is in-memory only and resets when the server process restarts.
"""

from datetime import datetime

_flight_store: dict[str, dict] = {}
_uid_index: dict[int, dict] = {}
_next_uid: int = 1
token_map: dict = {}
