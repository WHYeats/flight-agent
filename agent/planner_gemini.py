from google import genai
from google.genai import types
from fastmcp import Client
from config.settings import GEMINI_API_KEY, GEMINI_MODEL


def _clean_schema(schema: dict) -> dict:
    """Recursively remove fields unsupported by Gemini's Schema proto."""
    UNSUPPORTED = {"$schema", "title", "additionalProperties"}
    result = {}
    for k, v in schema.items():
        if k in UNSUPPORTED:
            continue
        if isinstance(v, dict):
            result[k] = _clean_schema(v)
        elif isinstance(v, list):
            result[k] = [_clean_schema(i) if isinstance(i, dict) else i for i in v]
        else:
            result[k] = v
    return result


def _mcp_tools_to_gemini(mcp_tools) -> list:
    """Convert MCP tool definitions to Gemini function declarations."""
    declarations = []
    for tool in mcp_tools:
        schema = _clean_schema(tool.inputSchema)
        declarations.append(
            types.FunctionDeclaration(
                name=tool.name,
                description=tool.description or "",
                parameters=schema,
            )
        )
    return [types.Tool(function_declarations=declarations)]


async def _send_and_loop(chat, mcp_client, user_message: str) -> str:
    """Send one user message and run the tool-call loop until a text response."""
    response = await chat.send_message(user_message)

    while True:
        fn_calls = [
            p.function_call
            for p in response.candidates[0].content.parts
            if p.function_call
        ]

        if not fn_calls:
            return response.text

        tool_parts = []
        for fn in fn_calls:
            tool_result = await mcp_client.call_tool(fn.name, dict(fn.args))
            tool_parts.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name=fn.name,
                        response={"result": str(tool_result)},
                    )
                )
            )

        response = await chat.send_message(tool_parts)


async def run_session(on_response) -> None:
    """
    Run a full multi-turn flight agent session using Gemini.
    Keeps the MCP server and chat session alive across turns.

    Args:
        on_response: async callable(response: str) -> str | None
                     Called with each agent response. Should return the next
                     user message, or None to end the session.
    """
    client = genai.Client(api_key=GEMINI_API_KEY)

    async with Client("mcp_server/server.py") as mcp_client:
        mcp_tools = await mcp_client.list_tools()
        gemini_tools = _mcp_tools_to_gemini(mcp_tools)

        system_prompt = """You are a flight search assistant. Follow these rules in every response:

1. Always present each flight option with its id number, e.g. "[1] KE 18 / KE 873".
2. Recommend the best option first with a brief reason (price, duration, or convenience).
3. For each option include: airline, flight numbers, price, departure/arrival times, stops.
4. When the user picks a flight by id or flight number, call get_booking_options with the correct id.
5. Show the booking URL to the user and tell them to open it in a browser to complete booking.
6. If a search returns no results, suggest relaxing constraints (budget, stops, time window).
7. Only one-way flights are supported. If the user asks for round-trip or multi-city, tell them it is not yet supported."""

        config = types.GenerateContentConfig(tools=gemini_tools, system_instruction=system_prompt)
        chat = client.aio.chats.create(model=GEMINI_MODEL, config=config)

        user_message = await on_response(None)  # get first message
        while user_message:
            response = await _send_and_loop(chat, mcp_client, user_message)
            user_message = await on_response(response)
