from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.tasks.service import create_task, update_task_status, list_tasks

router = APIRouter(prefix="/tasks", tags=["tasks"])

class CreateTaskRequest(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"

class UpdateStatusRequest(BaseModel):
    status: str

# Simplified: owner_id would come from auth middleware in production
@router.post("/", status_code=201)
def create(req: CreateTaskRequest, owner_id: str = "test-user", db: Session = Depends(get_db)):
    return create_task(db, owner_id, req.title, req.description, req.priority)

@router.patch("/{task_id}/status")
def update_status(task_id: str, req: UpdateStatusRequest, owner_id: str = "test-user", db: Session = Depends(get_db)):
    try:
        return update_task_status(db, task_id, owner_id, req.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/")
def list_all(owner_id: str = "test-user", db: Session = Depends(get_db)):
    return list_tasks(db, owner_id)
