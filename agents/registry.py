
from dataclasses import dataclass

from models.metadata import AgentType


WORKER_DISPATCH_NAME = "agentmeet-agent"


@dataclass(frozen=True)
class AgentDefinition:
    agent_type: AgentType
    display_name: str
    description: str


AGENT_REGISTRY: dict[
    AgentType,
    AgentDefinition,
] = {
    AgentType.MINIMAL: AgentDefinition(
        agent_type=AgentType.MINIMAL,
        display_name="AgentMeet Minimal Agent",
        description=(
            "Development agent used to verify "
            "LiveKit room participation."
        ),
    ),
    AgentType.NOTES: AgentDefinition(
        agent_type=AgentType.NOTES,
        display_name="Note Taker",
        description=(
            "Creates meeting notes, decisions, "
            "and action items."
        ),
    ),
    AgentType.ASSISTANT: AgentDefinition(
        agent_type=AgentType.ASSISTANT,
        display_name="Active Assistant",
        description=(
            "Answers questions using meeting context "
            "and approved tools."
        ),
    ),
    AgentType.TRANSLATOR: AgentDefinition(
        agent_type=AgentType.TRANSLATOR,
        display_name="Translator",
        description=(
            "Provides translated meeting captions."
        ),
    ),
}


def get_agent_definition(
    agent_type: AgentType | str,
) -> AgentDefinition:
    try:
        parsed_type = AgentType(agent_type)
    except ValueError as error:
        raise ValueError(
            "Unsupported agent type."
        ) from error

    try:
        return AGENT_REGISTRY[parsed_type]
    except KeyError as error:
        raise ValueError(
            "Agent type is not registered."
        ) from error
