# ClipFlow

AI-powered video editing web app that auto-removes filler words, dead air, and repeated takes.

## Stack
- Frontend: Next.js 14 (App Router) + TypeScript + Tailwind CSS + Zustand
- Backend: Python 3.11+ / FastAPI + SQLAlchemy 2.0 + Alembic
- Video: FFmpeg (server-side)
- Transcription: Deepgram Nova-2 (with diarization)
- AI: Claude API (content analysis, duplicate detection)
- Storage: Local filesystem (MVP)

## Development

```bash
# Backend
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev  # port 3000
```

## Project Structure
- `frontend/` - Next.js app
- `backend/` - FastAPI app
- `storage/` - Local file storage (uploads, processed, exports)

## Key Patterns
- Transcript segments are the central data model connecting all processing stages
- Processing pipeline: Upload → Transcribe → Analyze (filler/silence/duplicates) → User Review → Render
- Frontend uses SSE for real-time processing progress updates
- Video preview uses client-side time-skipping (no re-render needed for preview)
