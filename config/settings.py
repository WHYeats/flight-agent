import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# Anthropic model config
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096

# Gemini model config
GEMINI_MODEL = "gemini-2.5-flash"
