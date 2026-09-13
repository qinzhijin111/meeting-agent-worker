
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
)


class AgentType(StrEnum):
    MINIMAL = "minimal"
    NOTES = "notes"
    ASSISTANT = "assistant"
    TRANSLATOR = "translator"


class AgentJobMetadata(BaseModel):
    """
    Metadata sent by the Next.js application
    when an agent is explicitly dispatched
    to a LiveKit room.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    room_id: UUID

    room_name: str = Field(
        min_length=1,
        max_length=255,
    )

    # UUID of the corresponding room_agents row.
    #
    # Week 6 uses this to associate persisted
    # meeting notes with the exact agent session.
    agent_session_id: UUID

    agent_type: AgentType

    started_by: UUID

    settings: dict[str, Any] = Field(
        default_factory=dict
    )


def parse_agent_job_metadata(
    raw_metadata: str,
) -> AgentJobMetadata:
    """
    Parse and validate JSON job metadata.

    Do not include raw metadata in validation
    errors because future metadata may contain
    information that should not be logged.
    """

    try:
        return (
            AgentJobMetadata
            .model_validate_json(
                raw_metadata
            )
        )

    except ValidationError as error:
        raise ValueError(
            "Invalid agent job metadata."
        ) from error
