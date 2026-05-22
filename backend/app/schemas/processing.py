from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProcessingJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    job_type: str
    status: str
    progress_pct: int
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class ProcessingStatusResponse(BaseModel):
    project_id: str
    jobs: list[ProcessingJobResponse]
    overall_status: str
    overall_progress_pct: int
