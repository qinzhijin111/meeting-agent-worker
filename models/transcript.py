
import time

from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    """One finalized transcript segment from one participant."""

    speaker_identity: str = Field(min_length=1)
    speaker_name: str | None = None

    track_sid: str = Field(min_length=1)

    text: str = Field(min_length=1)

    language: str | None = None
    confidence: float | None = None

    speech_start_time: float | None = None
    speech_end_time: float | None = None

    captured_at: float = Field(
        default_factory=time.time
    )
