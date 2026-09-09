
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class AgentType(StrEnum):
    MINIMAL = "minimal"
    NOTES = "notes"
    ASSISTANT = "assistant"
    TRANSLATOR = "translator"


class AgentJobMetadata(BaseModel):
    """
    Metadata sent by the Next.js application when an agent
    is explicitly dispatched to a LiveKit room.
    """

    model_config = ConfigDict(extra="forbid")

    room_id: UUID
    room_name: str = Field(min_length=1, max_length=255)
    agent_type: AgentType
    started_by: UUID
    settings: dict[str, Any] = Field(default_factory=dict)


def parse_agent_job_metadata(
    raw_metadata: str,
) -> AgentJobMetadata:
    """
    Parse and validate JSON job metadata.

    Never return the raw metadata in an error because future
    metadata may contain information that should not be logged.
    """

    try:
        return AgentJobMetadata.model_validate_json(
            raw_metadata
        )
    except ValidationError as error:
        raise ValueError(
            "Invalid agent job metadata."
        ) from error
