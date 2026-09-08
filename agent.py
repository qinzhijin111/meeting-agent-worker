
import asyncio
import json
import logging

from dotenv import load_dotenv
from livekit.agents import AgentServer, JobContext, cli


load_dotenv()

logger = logging.getLogger("agentmeet-minimal-agent")
logger.setLevel(logging.INFO)

AGENT_DISPATCH_NAME = "agentmeet-minimal"
AGENT_DISPLAY_NAME = "AgentMeet Minimal Agent"


server = AgentServer()


@server.rtc_session(agent_name=AGENT_DISPATCH_NAME)
async def entrypoint(ctx: JobContext) -> None:
    """
    Minimal Week 5 agent.

    It does not use STT, LLM, or TTS yet.
    Its only job is to join a LiveKit room and identify itself
    as an agent participant.
    """

    ctx.log_context_fields = {
        "room": ctx.room.name,
        "agent_name": AGENT_DISPATCH_NAME,
    }

    disconnected = asyncio.Event()

    @ctx.room.on("disconnected")
    def on_disconnected(_reason) -> None:
        logger.info("Agent disconnected from room.")
        disconnected.set()

    # Join the LiveKit room.
    await ctx.connect()

    participant = ctx.room.local_participant

    # Give the agent a human-readable display name.
    try:
        await participant.set_name(
            AGENT_DISPLAY_NAME
        )
    except Exception:
        logger.warning(
            "Unable to update agent display name."
        )

    # Metadata matches the format already understood
    # by the Week 4 MeetingRoom UI.
    try:
        await participant.set_metadata(
            json.dumps(
                {
                    "participantType": "agent",
                    "agentType": "minimal",
                }
            )
        )
    except Exception:
        logger.warning(
            "Unable to update agent metadata."
        )

    try:
        await participant.set_attributes(
            {
                "agent.type": "minimal",
                "agent.status": "ready",
            }
        )
    except Exception:
        logger.warning(
            "Unable to update agent attributes."
        )

    logger.info(
        "Minimal agent joined room.",
        extra={
            "room": ctx.room.name,
            "participant_identity": participant.identity,
            "participant_name": participant.name,
        },
    )

    # Keep the minimal participant alive until
    # LiveKit disconnects the job.
    await disconnected.wait()


if __name__ == "__main__":
    cli.run_app(server)
