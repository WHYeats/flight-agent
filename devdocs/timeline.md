# Flight Agent — Project Timeline

## Phase 1 — Setup & Foundation (Day 1)
- Initialize the project structure, `requirements.txt`, `.env`
- Set up Anthropic SDK and verify Claude API connection
- Set up MCP server skeleton with `fastmcp` library
- Confirm the agent can call a dummy tool successfully

---

## Phase 2 — Core MCP Tools (Day 2–4)
Build and test each tool independently:

- **Day 2:** `resolve_airports.py` — expand city names to major commercial airport codes
- **Day 3:** `flexible_dates.py` — expand a date range into a list of candidate dates
- **Day 4:** `search_flights.py` — call SerpAPI and apply pre-filtering (max stops, landing time, etc.)

Each tool should be testable standalone before wiring into MCP.

---

## Phase 3 — Agent Planner (Day 5–6)
- Write the tool-use loop in `agent/planner.py`
- Claude receives user prompt → calls MCP tools → receives filtered results → generates recommendation report
- LLM recommends based on price and user preferences

---

## Phase 4 — Integration & End-to-End Test (Day 7)
- Wire `main.py` to accept natural language input
- Run a real query: "Tokyo to Las Vegas, flexible dates in April, max 2 stops"
- Debug the full agent loop

---

## Phase 5 — Polish (Day 8–9)
- Clean up output formatting (present ranked results clearly)
- Add error handling (API failures, no results found)
- Write `tests/test_tools.py`
- Write a clear `README.md` for portfolio/interview purposes

---

## Suggested Order to Tackle Modules

| Order | Module | Role |
|-------|--------|------|
| 1 | `config/settings.py` + `.env` | Everything depends on this |
| 2 | `mcp_server/server.py` (skeleton) | Needed to register tools |
| 3 | `resolve_airports.py` | MCP — city → airport codes |
| 4 | `flexible_dates.py` | MCP — date range → list of dates |
| 5 | `search_flights.py` | MCP — SerpAPI call + pre-filtering |
| 6 | `agent/planner.py` | LLM — orchestration + final recommendation |
| 7 | `main.py` | Final integration |
| 8 | `tests/` + README | Polish |
