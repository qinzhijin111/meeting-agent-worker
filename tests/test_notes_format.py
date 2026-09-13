
import pytest
from pydantic import ValidationError

from models.outputs import (
    MeetingNotesOutput,
)


def test_valid_meeting_notes():
    notes = MeetingNotesOutput(
        summary=(
            "The team planned the "
            "next release."
        ),
        decisions=[
            "Release on Friday."
        ],
        action_items=[
            {
                "description":
                    "Prepare release notes.",
                "owner": "Bob",
                "due_date": "Friday",
            }
        ],
        open_questions=[
            "Who will monitor deployment?"
        ],
    )

    assert (
        notes.action_items[0].owner
        == "Bob"
    )


def test_unknown_field_is_rejected():
    with pytest.raises(
        ValidationError
    ):
        MeetingNotesOutput(
            summary="Test summary",
            decisions=[],
            action_items=[],
            open_questions=[],
            unexpected="not allowed",
        )
