from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    speaker_count: int = 1
    silence_threshold_ms: int = 500
    filler_words: list[str] | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    speaker_count: int | None = None
    silence_threshold_ms: int | None = None
    filler_words: list[str] | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    status: str
    speaker_count: int
    silence_threshold_ms: int
    filler_words: list[str]
    created_at: datetime
    updated_at: datetime
