
import asyncio
import json
import logging

from dotenv import load_dotenv
from livekit.agents import (
    AgentServer,
    JobContext,
    cli,
)

from agents.notes_agent import NoteTaker
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


# LiveKit Agent Server includes its own
# health endpoint. Modal supervises the
# worker through port 8081.
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
    Main AgentMeet worker entrypoint.

    Explicit-dispatch jobs contain validated
    metadata describing the requested agent.

    Local connect mode without metadata falls
    back to the minimal development agent.
    """

    ctx.log_context_fields = {
        "room": ctx.room.name,
        "agent_name":
            WORKER_DISPATCH_NAME,
    }

    job_metadata: (
        AgentJobMetadata | None
    ) = None

    note_taker: (
        NoteTaker | None
    ) = None

    # -------------------------------------------------
    # 1. Parse explicit-dispatch metadata
    # -------------------------------------------------

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

        # Never trust the metadata room name
        # without checking the actual LiveKit room.
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

        try:
            definition = (
                get_agent_definition(
                    job_metadata.agent_type
                )
            )

        except ValueError:
            logger.error(
                "Rejecting agent job because "
                "the requested agent type is "
                "not registered."
            )
            return

    else:
        # Local LiveKit `connect` mode may not
        # contain explicit-dispatch metadata.
        #
        # Keep the Week 5 minimal-agent fallback.
        definition = (
            get_agent_definition(
                AgentType.MINIMAL
            )
        )

    # -------------------------------------------------
    # 2. Watch for LiveKit room disconnect
    # -------------------------------------------------

    disconnected = asyncio.Event()

    @ctx.room.on(
        "disconnected"
    )
    def on_disconnected(
        _reason,
    ) -> None:
        logger.info(
            "Agent disconnected from room."
        )

        disconnected.set()

    # -------------------------------------------------
    # 3. Join the LiveKit room
    # -------------------------------------------------

    await ctx.connect()

    participant = (
        ctx.room.local_participant
    )

    # -------------------------------------------------
    # 4. Set visible AgentMeet participant metadata
    # -------------------------------------------------

    participant_metadata: dict[
        str,
        str,
    ] = {
        "participantType":
            "agent",

        "agentType":
            definition.agent_type.value,

        "displayName":
            definition.display_name,
    }

    if job_metadata is not None:
        participant_metadata[
            "roomId"
        ] = str(
            job_metadata.room_id
        )

        participant_metadata[
            "agentSessionId"
        ] = str(
            job_metadata.agent_session_id
        )

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
            "Unable to update agent "
            "metadata."
        )

    try:
        await participant.set_attributes(
            {
                "agent.type":
                    definition
                    .agent_type
                    .value,

                "agent.status":
                    "ready",
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
            "room":
                ctx.room.name,

            "participant_identity":
                participant.identity,

            "agent_type":
                definition
                .agent_type
                .value,
        },
    )

    # -------------------------------------------------
    # 5. Start agent-specific behavior
    # -------------------------------------------------

    if (
        definition.agent_type
        == AgentType.NOTES
    ):
        # Week 6 Note Taker requires explicit
        # dispatch metadata because output must
        # be associated with the correct room and
        # room_agents session.
        if job_metadata is None:
            logger.error(
                "Note Taker requires explicit "
                "dispatch metadata."
            )

            try:
                await participant.set_attributes(
                    {
                        "agent.type":
                            "notes",

                        "agent.status":
                            "error",
                    }
                )

            except Exception:
                logger.warning(
                    "Unable to update "
                    "Note Taker error status."
                )

            return

        try:
            note_taker = NoteTaker(
                ctx.room,
                room_id=str(
                    job_metadata.room_id
                ),
                agent_session_id=str(
                    job_metadata
                    .agent_session_id
                ),
            )

            note_taker.start()

        except Exception:
            logger.exception(
                "Unable to start "
                "Note Taker behavior."
            )

            try:
                await participant.set_attributes(
                    {
                        "agent.type":
                            "notes",

                        "agent.status":
                            "error",
                    }
                )

            except Exception:
                logger.warning(
                    "Unable to update "
                    "Note Taker error status."
                )

            return

        try:
            await participant.set_attributes(
                {
                    "agent.type":
                        "notes",

                    "agent.status":
                        "working",
                }
            )

        except Exception:
            logger.warning(
                "Unable to update "
                "Note Taker status."
            )

        logger.info(
            "Note Taker behavior is active.",
            extra={
                "room_id":
                    str(
                        job_metadata.room_id
                    ),

                "agent_session_id":
                    str(
                        job_metadata
                        .agent_session_id
                    ),
            },
        )

    elif (
        definition.agent_type
        == AgentType.ASSISTANT
    ):
        # Week 7 behavior is not implemented yet.
        logger.info(
            "Active Assistant joined, "
            "but its behavior is not "
            "implemented yet."
        )

    elif (
        definition.agent_type
        == AgentType.TRANSLATOR
    ):
        # Week 7 behavior is not implemented yet.
        logger.info(
            "Translator joined, "
            "but its behavior is not "
            "implemented yet."
        )

    else:
        # Minimal development agent.
        logger.info(
            "Minimal agent behavior active."
        )

    # -------------------------------------------------
    # 6. Keep the agent alive until disconnect
    # -------------------------------------------------

    try:
        await disconnected.wait()

    finally:
        # ---------------------------------------------
        # 7. Finalize Note Taker output
        # ---------------------------------------------

        if note_taker is not None:
            try:
                await (
                    note_taker
                    .finalize_and_persist()
                )

            except Exception:
                logger.exception(
                    "Unexpected error while "
                    "finalizing Note Taker."
                )

            finally:
                try:
                    await note_taker.aclose()

                except Exception:
                    logger.exception(
                        "Error while closing "
                        "Note Taker resources."
                    )

        logger.info(
            "Agent job cleanup complete.",
            extra={
                "room":
                    ctx.room.name,

                "agent_type":
                    definition
                    .agent_type
                    .value,
            },
        )


if __name__ == "__main__":
    cli.run_app(server)
