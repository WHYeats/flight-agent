import asyncio


async def main():
    print("Flight Agent")
    print("=" * 40)
    from agent.planner_gemini import run_session

    print("Type your message and press Enter. Type 'exit' or leave blank to quit.\n")

    async def on_response(response: str | None) -> str | None:
        if response is not None:
            print(f"\nAgent: {response}\n")
        user_input = input("You: ").strip()
        if not user_input or user_input.lower() == "exit":
            return None
        return user_input

    await run_session(on_response)
    print("\nSession ended.")


if __name__ == "__main__":
    asyncio.run(main())
