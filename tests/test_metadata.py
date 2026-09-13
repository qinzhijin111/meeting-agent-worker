
import json
from uuid import uuid4

import pytest

from models.metadata import (
    AgentType,
    parse_agent_job_metadata,
)


def make_valid_metadata():
    return json.dumps(
        {
            "room_id": str(
                uuid4()
            ),

            "room_name":
                "room_test",

            "agent_session_id": str(
                uuid4()
            ),

            "agent_type":
                "notes",

            "started_by": str(
                uuid4()
            ),

            "settings": {},
        }
    )



def test_valid_metadata():
    metadata = (
        parse_agent_job_metadata(
            make_valid_metadata()
        )
    )

    assert (
        metadata.agent_type
        == AgentType.NOTES
    )

    assert (
        metadata.room_name
        == "room_test"
    )


def test_invalid_agent_type():
    payload = json.loads(
        make_valid_metadata()
    )

    payload["agent_type"] = (
        "unknown-agent"
    )

    with pytest.raises(ValueError):
        parse_agent_job_metadata(
            json.dumps(payload)
        )


def test_missing_room_name():
    payload = json.loads(
        make_valid_metadata()
    )

    del payload["room_name"]

    with pytest.raises(ValueError):
        parse_agent_job_metadata(
            json.dumps(payload)
        )


def test_unexpected_field():
    payload = json.loads(
        make_valid_metadata()
    )

    payload["unexpected"] = "value"

    with pytest.raises(ValueError):
        parse_agent_job_metadata(
            json.dumps(payload)
        )
