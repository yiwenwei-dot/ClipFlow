import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

DEFAULT_FILLER_WORDS = [
    "um", "uh", "er", "ah", "like", "you know",
    "so", "actually", "basically", "right", "okay",
]


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    speaker_count: Mapped[int] = mapped_column(Integer, default=1)
    silence_threshold_ms: Mapped[int] = mapped_column(Integer, default=500)
    filler_words: Mapped[list] = mapped_column(
        JSON, default=lambda: list(DEFAULT_FILLER_WORDS)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    clips = relationship("Clip", back_populates="project", cascade="all, delete-orphan")
    speakers = relationship("Speaker", back_populates="project", cascade="all, delete-orphan")
    processing_jobs = relationship(
        "ProcessingJob", back_populates="project", cascade="all, delete-orphan"
    )
    exports = relationship("Export", back_populates="project", cascade="all, delete-orphan")
