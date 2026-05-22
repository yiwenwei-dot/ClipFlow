import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    clip_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clips.id", ondelete="CASCADE"), nullable=False
    )
    speaker_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("speakers.id", ondelete="SET NULL"), nullable=True
    )
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    word_timestamps: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    segment_type: Mapped[str] = mapped_column(String(20), default="speech")
    cut_decision: Mapped[str] = mapped_column(String(20), default="keep")
    cut_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    duplicate_group_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    clip = relationship("Clip", back_populates="segments")
    speaker = relationship("Speaker", back_populates="segments")
