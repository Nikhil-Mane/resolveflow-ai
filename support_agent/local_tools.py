"""Four local LangChain tools: REST API, RAG, LLM, and SQLite."""

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool, tool


MODULE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = MODULE_DIR / "support.db"
KNOWLEDGE_PATH = MODULE_DIR / "knowledge_base.md"


def initialize_database() -> None:
    """Create a tiny local database and insert repeatable sample rows."""

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                product TEXT NOT NULL,
                status TEXT NOT NULL,
                total REAL NOT NULL
            )
            """
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO orders
                (order_id, customer_name, product, status, total)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("ORD-101", "Nikhil", "Mechanical Keyboard", "shipped", 79.99),
                ("ORD-102", "Asha", "Wireless Mouse", "processing", 29.50),
                ("ORD-103", "Ravi", "USB-C Hub", "delivered", 45.00),
            ],
        )
        connection.commit()


def _sections_from_knowledge_base() -> list[str]:
    text = KNOWLEDGE_PATH.read_text(encoding="utf-8")
    return [section.strip() for section in re.split(r"(?=^## )", text, flags=re.MULTILINE) if section.startswith("## ")]


def _keywords(text: str) -> set[str]:
    stop_words = {
        "a", "an", "and", "are", "can", "do", "for", "how", "i", "in",
        "is", "it", "my", "of", "on", "the", "to", "what", "when", "with",
    }
    normalized: set[str] = set()
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        if token in stop_words or len(token) <= 1:
            continue
        # Tiny educational stemmer: return/returns/returned should match.
        for suffix in ("ing", "ed", "es", "s"):
            if token.endswith(suffix) and len(token) - len(suffix) >= 4:
                token = token[: -len(suffix)]
                break
        normalized.add(token)
    return normalized


def build_local_tools(model: BaseChatModel) -> list[BaseTool]:
    """Build the four non-MCP tools used by the agent."""

    initialize_database()

    @tool
    def get_public_todo(todo_id: int) -> str:
        """Fetch a sample todo from a public REST API by numeric todo ID (1-200)."""

        if not 1 <= todo_id <= 200:
            return "todo_id must be between 1 and 200."
        url = f"https://jsonplaceholder.typicode.com/todos/{todo_id}"
        try:
            response = httpx.get(url, timeout=8.0, follow_redirects=True)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            return json.dumps(
                {
                    "id": data.get("id"),
                    "title": data.get("title"),
                    "completed": data.get("completed"),
                }
            )
        except (httpx.HTTPError, ValueError) as error:
            return f"The REST API request failed: {type(error).__name__}."

    @tool
    def search_support_policies(question: str) -> str:
        """Retrieve relevant return, refund, shipping, or warranty policy text."""

        query_terms = _keywords(question)
        ranked: list[tuple[int, str]] = []
        for section in _sections_from_knowledge_base():
            score = len(query_terms & _keywords(section))
            ranked.append((score, section))
        matches = [section for score, section in sorted(ranked, reverse=True) if score > 0]
        if not matches:
            return "No relevant support-policy passage was found."
        return "\n\n".join(matches[:2])

    @tool
    def answer_general_question(question: str) -> str:
        """Use a plain LLM call for general explanations that need no private or live data."""

        response = model.invoke(
            [
                ("system", "Give a clear beginner-friendly answer in at most three sentences."),
                ("human", question),
            ]
        )
        return response.text

    @tool
    def lookup_order(order_id: str) -> str:
        """Read one sample order from SQLite using an ID such as ORD-101."""

        normalized_id = order_id.strip().upper()
        if not re.fullmatch(r"ORD-\d{3}", normalized_id):
            return "Use an order ID in the form ORD-101."
        with sqlite3.connect(DATABASE_PATH) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                SELECT order_id, customer_name, product, status, total
                FROM orders
                WHERE order_id = ?
                """,
                (normalized_id,),
            ).fetchone()
        if row is None:
            return f"No order was found for {normalized_id}."
        return json.dumps(dict(row))

    return [
        get_public_todo,
        search_support_policies,
        answer_general_question,
        lookup_order,
    ]
