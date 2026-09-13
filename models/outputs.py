
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class ActionItem(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    description: str = Field(
        min_length=1,
        max_length=1000,
    )

    owner: str | None = Field(
        default=None,
        max_length=200,
    )

    due_date: str | None = Field(
        default=None,
        max_length=200,
    )


class MeetingNotesOutput(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    summary: str = Field(
        min_length=1,
        max_length=10000,
    )

    decisions: list[str] = Field(
        default_factory=list,
        max_length=100,
    )

    action_items: list[ActionItem] = Field(
        default_factory=list,
        max_length=100,
    )

    open_questions: list[str] = Field(
        default_factory=list,
        max_length=100,
    )
