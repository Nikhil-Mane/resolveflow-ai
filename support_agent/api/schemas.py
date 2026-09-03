"""Validated HTTP request and response contracts."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


IDENTIFIER_PATTERN = r"^[A-Za-z0-9_-]+$"


class ChatRequest(BaseModel):
    """One message sent by one user to one conversation thread."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    message: str = Field(min_length=1, max_length=4_000)
    user_id: str = Field(min_length=1, max_length=100, pattern=IDENTIFIER_PATTERN)
    thread_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=IDENTIFIER_PATTERN,
    )

    @field_validator("message")
    @classmethod
    def reject_blank_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        return value


class ChatResponse(BaseModel):
    """The agent answer and identifiers needed for the next turn."""

    answer: str
    user_id: str
    thread_id: str
    tools_used: list[str]


class HealthResponse(BaseModel):
    """Small response returned by the liveness endpoint."""

    status: str
