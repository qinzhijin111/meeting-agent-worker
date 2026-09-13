
import asyncio
import json
import logging
from collections.abc import Callable

from livekit import rtc
from livekit.agents import (
    ChatContext,
    inference,
    stt,
)

from models.outputs import MeetingNotesOutput
from models.transcript import TranscriptSegment
from tools.persistence import NotesPersistenceClient


logger = logging.getLogger(
    "agentmeet-notes"
)


class TrackTranscriber:
    """
    Transcribes one participant audio track.

    One TrackTranscriber corresponds to one
    remote human microphone track.
    """

    def __init__(
        self,
        *,
        track: rtc.RemoteAudioTrack,
        participant: rtc.RemoteParticipant,
        stt_model: inference.STT,
        on_final_segment: Callable[
            [TranscriptSegment],
            None,
        ],
    ) -> None:
        self._track = track
        self._participant = participant
        self._on_final_segment = (
            on_final_segment
        )

        self._stt_stream = (
            stt_model.stream()
        )

        self._tasks: list[
            asyncio.Task
        ] = []

    def start(self) -> None:
        """
        Start audio consumption and
        transcript consumption tasks.
        """

        self._tasks.append(
            asyncio.create_task(
                self._consume_audio()
            )
        )

        self._tasks.append(
            asyncio.create_task(
                self._consume_transcripts()
            )
        )

    async def _consume_audio(
        self,
    ) -> None:
        """
        Read LiveKit audio frames and send
        them into the STT stream.
        """

        audio_stream = (
            rtc.AudioStream.from_track(
                track=self._track
            )
        )

        try:
            async for event in audio_stream:
                self._stt_stream.push_frame(
                    event.frame
                )

        finally:
            self._stt_stream.end_input()

            await audio_stream.aclose()

    async def _consume_transcripts(
        self,
    ) -> None:
        """
        Collect only FINAL_TRANSCRIPT events.

        Interim transcripts are intentionally
        ignored because they may still change.
        """

        async for event in self._stt_stream:
            if (
                event.type
                != stt.SpeechEventType.FINAL_TRANSCRIPT
            ):
                continue

            if not event.alternatives:
                continue

            alternative = (
                event.alternatives[0]
            )

            text = (
                alternative.text.strip()
            )

            if not text:
                continue

            segment = TranscriptSegment(
                speaker_identity=(
                    self._participant.identity
                ),
                speaker_name=(
                    self._participant.name
                    or None
                ),
                track_sid=self._track.sid,
                text=text,
                language=(
                    alternative.language
                    or None
                ),
                confidence=(
                    alternative.confidence
                ),
                speech_start_time=(
                    event.speech_start_time
                ),
                speech_end_time=(
                    event.speech_end_time
                ),
            )

            self._on_final_segment(
                segment
            )

    async def aclose(self) -> None:
        """
        Stop the audio/STT tasks for this
        participant track.
        """

        for task in self._tasks:
            task.cancel()

        if self._tasks:
            await asyncio.gather(
                *self._tasks,
                return_exceptions=True,
            )

        self._tasks.clear()

        await self._stt_stream.aclose()


class NoteTaker:
    """
    Passive meeting Note Taker.

    Responsibilities:
    - Listen to human microphone tracks.
    - Collect finalized transcript segments.
    - Associate transcript with speaker identity.
    - Generate structured meeting notes.
    - Persist notes through the protected
      AgentMeet server endpoint.
    """

    def __init__(
        self,
        room: rtc.Room,
        *,
        room_id: str,
        agent_session_id: str,
    ) -> None:
        self._room = room

        self._room_id = room_id

        self._agent_session_id = (
            agent_session_id
        )

        # -----------------------------------------
        # Speech-to-text
        # -----------------------------------------

        self._stt = inference.STT(
            model="deepgram/nova-3",
            language="multi",
        )

        # -----------------------------------------
        # LLM for structured notes
        # -----------------------------------------

        self._llm = inference.LLM(
            model="openai/gpt-5-mini",
        )

        # -----------------------------------------
        # Task 4 persistence client
        #
        # Creating this client does not need to
        # fail if persistence is not configured.
        # The client checks configuration when
        # persistence is actually attempted.
        # -----------------------------------------

        self._persistence = (
            NotesPersistenceClient(
                room_id=room_id,
                agent_session_id=(
                    agent_session_id
                ),
            )
        )

        # -----------------------------------------
        # Active participant transcribers
        # -----------------------------------------

        self._transcribers: dict[
            str,
            TrackTranscriber,
        ] = {}

        self._cleanup_tasks: set[
            asyncio.Task
        ] = set()

        # -----------------------------------------
        # Final transcript segments
        # -----------------------------------------

        self.segments: list[
            TranscriptSegment
        ] = []

    def start(self) -> None:
        """
        Start listening for human audio tracks.
        """

        logger.info(
            "Note Taker transcription started."
        )

        @self._room.on(
            "track_subscribed"
        )
        def on_track_subscribed(
            track: rtc.Track,
            publication: rtc.RemoteTrackPublication,
            participant: rtc.RemoteParticipant,
        ) -> None:
            # Ignore non-audio tracks.
            if not isinstance(
                track,
                rtc.RemoteAudioTrack,
            ):
                return

            # Never transcribe another AI agent.
            if self._is_agent_participant(
                participant
            ):
                return

            self._add_track(
                track,
                participant,
            )

        @self._room.on(
            "track_unsubscribed"
        )
        def on_track_unsubscribed(
            track: rtc.Track,
            publication: rtc.RemoteTrackPublication,
            participant: rtc.RemoteParticipant,
        ) -> None:
            if not isinstance(
                track,
                rtc.RemoteAudioTrack,
            ):
                return

            self._remove_track(
                track.sid
            )

        # -----------------------------------------
        # Handle humans who were already present
        # before the Note Taker joined.
        # -----------------------------------------

        for participant in (
            self._room
            .remote_participants
            .values()
        ):
            if self._is_agent_participant(
                participant
            ):
                continue

            for publication in (
                participant
                .track_publications
                .values()
            ):
                track = publication.track

                if isinstance(
                    track,
                    rtc.RemoteAudioTrack,
                ):
                    self._add_track(
                        track,
                        participant,
                    )

    def _add_track(
        self,
        track: rtc.RemoteAudioTrack,
        participant: rtc.RemoteParticipant,
    ) -> None:
        """
        Start transcription for a newly
        subscribed human audio track.
        """

        if (
            track.sid
            in self._transcribers
        ):
            return

        logger.info(
            "Starting transcription "
            "for participant=%s track=%s",
            participant.identity,
            track.sid,
        )

        transcriber = TrackTranscriber(
            track=track,
            participant=participant,
            stt_model=self._stt,
            on_final_segment=(
                self._handle_final_segment
            ),
        )

        self._transcribers[
            track.sid
        ] = transcriber

        transcriber.start()

    def _remove_track(
        self,
        track_sid: str,
    ) -> None:
        """
        Stop transcription for a track
        that was unsubscribed.
        """

        transcriber = (
            self._transcribers.pop(
                track_sid,
                None,
            )
        )

        if transcriber is None:
            return

        task = asyncio.create_task(
            transcriber.aclose()
        )

        self._cleanup_tasks.add(
            task
        )

        task.add_done_callback(
            self._cleanup_tasks.discard
        )

    def _handle_final_segment(
        self,
        segment: TranscriptSegment,
    ) -> None:
        """
        Store one finalized transcript segment.
        """

        self.segments.append(
            segment
        )

        speaker = (
            segment.speaker_name
            or segment.speaker_identity
        )

        # Development-only logging.
        #
        # Use synthetic/demo speech when testing.
        # Do not log private production meetings.
        logger.info(
            "[FINAL] %s: %s",
            speaker,
            segment.text,
        )

    async def generate_notes(
        self,
    ) -> MeetingNotesOutput:
        """
        Convert finalized transcript segments
        into validated structured meeting notes.

        This method is Task 3.

        It deliberately does not perform
        persistence.
        """

        # -----------------------------------------
        # No-speech case
        # -----------------------------------------

        if not self.segments:
            return MeetingNotesOutput(
                summary=(
                    "No meaningful speech "
                    "was captured."
                ),
                decisions=[],
                action_items=[],
                open_questions=[],
            )

        # -----------------------------------------
        # Convert transcript segments into
        # readable speaker-labelled transcript.
        # -----------------------------------------

        transcript_lines: list[
            str
        ] = []

        for segment in self.segments:
            speaker = (
                segment.speaker_name
                or segment.speaker_identity
            )

            transcript_lines.append(
                f"{speaker}: "
                f"{segment.text}"
            )

        transcript = "\n".join(
            transcript_lines
        )

        # -----------------------------------------
        # Build LLM prompt
        # -----------------------------------------

        chat_ctx = ChatContext()

        chat_ctx.add_message(
            role="system",
            content=(
                "You are a meeting note taker. "
                "Create accurate structured notes "
                "using only information explicitly "
                "supported by the transcript. "
                "Do not invent decisions, owners, "
                "deadlines, or facts. "
                "If an action-item owner or due "
                "date is unknown, use null. "
                "If there are no decisions, "
                "action items, or open questions, "
                "return empty arrays. "
                "Keep the summary concise."
            ),
        )

        chat_ctx.add_message(
            role="user",
            content=(
                "Create meeting notes from "
                "this transcript:\n\n"
                f"{transcript}"
            ),
        )

        # -----------------------------------------
        # Generate structured result
        # -----------------------------------------

        response = await (
            self._llm.chat(
                chat_ctx=chat_ctx,
                response_format=(
                    MeetingNotesOutput
                ),
            )
            .collect()
        )

        # -----------------------------------------
        # Validate output again with Pydantic
        # -----------------------------------------

        notes = (
            MeetingNotesOutput
            .model_validate_json(
                response.text
            )
        )

        logger.info(
            "Structured meeting notes "
            "generated."
        )

        return notes

    async def finalize_and_persist(
        self,
    ) -> MeetingNotesOutput | None:
        """
        Finalize transcript collection,
        generate Task 3 structured notes,
        then attempt Task 4 persistence.

        Important design rule:

        Note generation and persistence are
        intentionally separated.

        A persistence failure must not destroy
        successfully generated structured notes.
        """

        logger.info(
            "Finalizing meeting notes."
        )

        # -----------------------------------------
        # 1. Stop transcript collection
        # -----------------------------------------

        await self._stop_transcribers()

        # -----------------------------------------
        # 2. Best-effort "processing" state
        # -----------------------------------------

        if (
            self._persistence
            .is_configured
        ):
            try:
                await self._persistence.save(
                    status="processing"
                )

                logger.info(
                    "Meeting notes marked "
                    "as processing."
                )

            except Exception:
                # Do NOT stop Task 3 generation
                # just because status persistence
                # failed.
                logger.exception(
                    "Unable to persist "
                    "processing state."
                )

        else:
            logger.warning(
                "Meeting-note persistence "
                "is not configured. "
                "Structured notes will still "
                "be generated."
            )

        # -----------------------------------------
        # 3. Task 3:
        # Generate structured meeting notes
        # -----------------------------------------

        try:
            notes = (
                await self.generate_notes()
            )

        except Exception:
            logger.exception(
                "Structured meeting-note "
                "generation failed."
            )

            # Best-effort error persistence.
            if (
                self._persistence
                .is_configured
            ):
                try:
                    await self._persistence.save(
                        status="error",
                        error_message=(
                            "Meeting note "
                            "generation failed."
                        ),
                    )

                except Exception:
                    logger.exception(
                        "Unable to persist "
                        "generation error state."
                    )

            return None

        # -----------------------------------------
        # 4. Task 4:
        # Persist successfully generated notes
        # -----------------------------------------

        if not (
            self._persistence
            .is_configured
        ):
            logger.warning(
                "Structured notes were generated "
                "successfully, but persistence "
                "is not configured."
            )

            # Task 3 still succeeded.
            return notes

        try:
            await self._persistence.save(
                status="ready",
                notes=notes,
            )

            logger.info(
                "Meeting notes persisted."
            )

        except Exception:
            # The notes still exist in memory
            # and Task 3 has succeeded.
            logger.exception(
                "Structured notes were generated "
                "but could not be persisted."
            )

            # Best-effort error status.
            try:
                failure_status = (
                    "partial"
                    if self.segments
                    else "error"
)

                error_message = (
                    "Final meeting note generation "
                    "failed after transcript segments "
                    "had already been captured."
                    if self.segments
                    else
                    "Meeting note generation failed "
                    "before usable transcript output "
                    "was available."
                )

                await self._persistence.save(
                    status=failure_status,
                    error_message=(
                        error_message
                    ),
                )


            except Exception:
                logger.exception(
                    "Unable to persist "
                    "persistence error state."
                )

        return notes

    async def _stop_transcribers(
        self,
    ) -> None:
        """
        Stop all current participant
        transcription streams.

        Safe to call more than once.
        """

        transcribers = list(
            self._transcribers.values()
        )

        self._transcribers.clear()

        if transcribers:
            await asyncio.gather(
                *(
                    transcriber.aclose()
                    for transcriber
                    in transcribers
                ),
                return_exceptions=True,
            )

        if self._cleanup_tasks:
            await asyncio.gather(
                *self._cleanup_tasks,
                return_exceptions=True,
            )

            self._cleanup_tasks.clear()

    @staticmethod
    def _is_agent_participant(
        participant: rtc.RemoteParticipant,
    ) -> bool:
        """
        Determine whether a remote participant
        is an AgentMeet AI participant.
        """

        # Preferred Week 5 participant
        # attribute.
        if participant.attributes.get(
            "agent.type"
        ):
            return True

        # Fallback to participant metadata.
        try:
            metadata = json.loads(
                participant.metadata
                or "{}"
            )

        except json.JSONDecodeError:
            return False

        return (
            metadata.get(
                "participantType"
            )
            == "agent"
        )

    async def aclose(self) -> None:
        """
        Release Note Taker resources.

        Safe to call after
        finalize_and_persist().
        """

        await self._stop_transcribers()

        await self._stt.aclose()

        await self._llm.aclose()

        logger.info(
            "Note Taker stopped with "
            "%d final transcript segments.",
            len(self.segments),
        )
