import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastmcp import FastMCP

from mcp_server.tools.resolve_airports import resolve_airports
from mcp_server.tools.search_flight_workflow import search_flight_workflow
from mcp_server.tools.get_booking_options import get_booking_options

mcp = FastMCP("flight-agent")

mcp.tool()(resolve_airports)
mcp.tool()(search_flight_workflow)
mcp.tool()(get_booking_options)


if __name__ == "__main__":
    mcp.run()
