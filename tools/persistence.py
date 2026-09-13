
import logging
import os

import httpx

from models.outputs import MeetingNotesOutput


logger = logging.getLogger(
    "agentmeet-persistence"
)


class NotesPersistenceError(
    RuntimeError
):
    """Raised when note persistence fails."""


class NotesPersistenceClient:
    """
    Sends meeting-note output from the
    Python worker to the protected Next.js API.

    Configuration errors do NOT occur during
    __init__, so persistence configuration
    cannot prevent the Note Taker from starting.
    """

    def __init__(
        self,
        *,
        room_id: str,
        agent_session_id: str,
    ) -> None:
        self._room_id = room_id

        self._agent_session_id = (
            agent_session_id
        )

        self._url = (
            os.getenv(
                "AGENT_OUTPUT_URL"
            )
            or ""
        ).strip()

        self._secret = (
            os.getenv(
                "AGENT_WORKER_SHARED_SECRET"
            )
            or ""
        ).strip()

    @property
    def is_configured(
        self,
    ) -> bool:
        return bool(
            self._url
            and self._secret
        )

    def _require_configuration(
        self,
    ) -> None:
        missing: list[str] = []

        if not self._url:
            missing.append(
                "AGENT_OUTPUT_URL"
            )

        if not self._secret:
            missing.append(
                "AGENT_WORKER_SHARED_SECRET"
            )

        if missing:
            raise NotesPersistenceError(
                "Missing persistence "
                "configuration: "
                + ", ".join(missing)
            )

    async def save(
        self,
        *,
        status: str,
        notes: MeetingNotesOutput
        | None = None,
        error_message: str
        | None = None,
    ) -> None:
        self._require_configuration()

        payload: dict[
            str,
            object,
        ] = {
            "roomId":
                self._room_id,

            "agentSessionId":
                self._agent_session_id,

            "status":
                status,
        }

        if notes is not None:
            payload["notes"] = {
                "summary":
                    notes.summary,

                "decisions":
                    notes.decisions,

                "actionItems": [
                    {
                        "description":
                            item.description,

                        "owner":
                            item.owner,

                        "dueDate":
                            item.due_date,
                    }
                    for item
                    in notes.action_items
                ],

                "openQuestions":
                    notes.open_questions,
            }

        if error_message is not None:
            payload[
                "errorMessage"
            ] = error_message

        headers = {
            "Authorization":
                f"Bearer {self._secret}",
        }

        try:
            async with (
                httpx.AsyncClient(
                    timeout=15.0
                ) as client
            ):
                response = (
                    await client.post(
                        self._url,
                        json=payload,
                        headers=headers,
                    )
                )

                response.raise_for_status()

        except httpx.HTTPStatusError as error:
            logger.error(
                "Agent output endpoint "
                "returned HTTP %s.",
                error.response.status_code,
            )

            raise NotesPersistenceError(
                "Agent output endpoint "
                "rejected the request."
            ) from error

        except httpx.HTTPError as error:
            logger.error(
                "Unable to reach the "
                "agent output endpoint."
            )

            raise NotesPersistenceError(
                "Unable to reach the "
                "agent output endpoint."
            ) from error
