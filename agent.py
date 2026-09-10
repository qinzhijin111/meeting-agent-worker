
import asyncio
import json
import logging

from dotenv import load_dotenv
from livekit.agents import (
    AgentServer,
    JobContext,
    cli,
)

from agents.registry import (
    WORKER_DISPATCH_NAME,
    get_agent_definition,
)
from models.metadata import (
    AgentJobMetadata,
    AgentType,
    parse_agent_job_metadata,
)


load_dotenv()

logger = logging.getLogger(
    "agentmeet-agent"
)
logger.setLevel(logging.INFO)


server = AgentServer(
    host="0.0.0.0",
    port=8081,
)


@server.rtc_session(
    agent_name=WORKER_DISPATCH_NAME
)
async def entrypoint(
    ctx: JobContext,
) -> None:
    """
    Modular AgentMeet worker entrypoint.

    Local connect mode falls back to the minimal agent.

    Explicit-dispatch jobs validate JSON metadata
    before joining the room.
    """

    ctx.log_context_fields = {
        "room": ctx.room.name,
        "agent_name": WORKER_DISPATCH_NAME,
    }

    job_metadata: AgentJobMetadata | None = None

    raw_metadata = (
        ctx.job.metadata or ""
    ).strip()

    if raw_metadata:
        try:
            job_metadata = (
                parse_agent_job_metadata(
                    raw_metadata
                )
            )
        except ValueError:
            logger.error(
                "Rejecting agent job because "
                "metadata is invalid."
            )
            return

        if (
            job_metadata.room_name
            != ctx.room.name
        ):
            logger.error(
                "Rejecting agent job because "
                "metadata room name does not "
                "match the assigned room."
            )
            return

        definition = get_agent_definition(
            job_metadata.agent_type
        )

    else:
        # Local `connect` mode does not require
        # dispatch metadata.
        definition = get_agent_definition(
            AgentType.MINIMAL
        )

    disconnected = asyncio.Event()

    @ctx.room.on("disconnected")
    def on_disconnected(_reason) -> None:
        logger.info(
            "Agent disconnected from room."
        )
        disconnected.set()

    await ctx.connect()

    participant = (
        ctx.room.local_participant
    )

    participant_metadata = {
        "participantType": "agent",
        "agentType": (
            definition.agent_type.value
        ),
        "displayName": (
            definition.display_name
        ),
    }

    if job_metadata is not None:
        participant_metadata[
            "roomId"
        ] = str(job_metadata.room_id)

    try:
        await participant.set_name(
            definition.display_name
        )
    except Exception:
        logger.warning(
            "Unable to update agent "
            "display name."
        )

    try:
        await participant.set_metadata(
            json.dumps(
                participant_metadata
            )
        )
    except Exception:
        logger.warning(
            "Unable to update agent metadata."
        )

    try:
        await participant.set_attributes(
            {
                "agent.type": (
                    definition.agent_type.value
                ),
                "agent.status": "ready",
            }
        )
    except Exception:
        logger.warning(
            "Unable to update agent "
            "attributes."
        )

    logger.info(
        "Agent joined room.",
        extra={
            "room": ctx.room.name,
            "participant_identity": (
                participant.identity
            ),
            "agent_type": (
                definition.agent_type.value
            ),
        },
    )

    await disconnected.wait()


if __name__ == "__main__":
    cli.run_app(server)
