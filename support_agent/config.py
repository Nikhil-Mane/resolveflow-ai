"""Azure OpenAI configuration shared by the agent and its LLM tool."""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def required_env(name: str) -> str:
    """Return a required environment variable without exposing its value."""

    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing {name}. Add it to {PROJECT_ROOT / '.env'}")
    return value


def create_model() -> ChatOpenAI:
    """Create an unbound Azure OpenAI chat model using the v1 endpoint."""

    endpoint = required_env("AZURE_OPENAI_ENDPOINT").rstrip("/")
    return ChatOpenAI(
        model=required_env("AZURE_OPENAI_DEPLOYMENT"),
        base_url=f"{endpoint}/openai/v1/",
        api_key=required_env("AZURE_OPENAI_API_KEY"),
        temperature=0,
        max_retries=2,
    )
