from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate, db: AsyncSession = Depends(get_db)
) -> Project:
    project = Project(
        name=data.name,
        description=data.description,
        speaker_count=data.speaker_count,
        silence_threshold_ms=data.silence_threshold_ms,
    )
    if data.filler_words is not None:
        project.filler_words = data.filler_words
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


@router.get("", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)) -> list[Project]:
    result = await db.execute(
        select(Project).order_by(Project.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> Project:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str, data: ProjectUpdate, db: AsyncSession = Depends(get_db)
) -> Project:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.flush()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> None:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
