import anthropic
from fastmcp import Client
from config.settings import ANTHROPIC_API_KEY, MODEL, MAX_TOKENS


async def _send_and_loop(anthropic_client, tools, messages, mcp_client) -> str:
    """Send current messages and run the tool-call loop until a text response."""
    while True:
        response = anthropic_client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            tools=tools,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = await mcp_client.call_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})


async def run_session(on_response) -> None:
    """
    Run a full multi-turn flight agent session using Claude.
    Keeps the MCP server and conversation history alive across turns.

    Args:
        on_response: async callable(response: str | None) -> str | None
                     Called with each agent response. Should return the next
                     user message, or None to end the session.
    """
    anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    async with Client("mcp_server/server.py") as mcp_client:
        mcp_tools = await mcp_client.list_tools()
        tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in mcp_tools
        ]

        messages = []
        user_message = await on_response(None)  # get first message
        while user_message:
            messages.append({"role": "user", "content": user_message})
            response = await _send_and_loop(anthropic_client, tools, messages, mcp_client)
            messages.append({"role": "assistant", "content": response})
            user_message = await on_response(response)
