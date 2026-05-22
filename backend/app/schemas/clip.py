from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    filename: str
    storage_path: str
    sequence_order: int
    duration_ms: int | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    file_size_bytes: int | None = None
    status: str
    created_at: datetime


class ClipReorderItem(BaseModel):
    id: str
    sequence_order: int


class ClipReorderRequest(BaseModel):
    clips: list[ClipReorderItem]
