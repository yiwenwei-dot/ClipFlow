from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    clip_id: str
    speaker_id: str | None = None
    start_ms: int
    end_ms: int
    text: str
    confidence: float | None = None
    word_timestamps: dict | None = None
    segment_type: str
    cut_decision: str
    cut_reason: str | None = None
    duplicate_group_id: str | None = None
    quality_score: float | None = None
    created_at: datetime


class SegmentUpdateRequest(BaseModel):
    cut_decision: str | None = None
    speaker_id: str | None = None
    text: str | None = None


class BulkSegmentUpdateRequest(BaseModel):
    segment_ids: list[str]
    cut_decision: str
