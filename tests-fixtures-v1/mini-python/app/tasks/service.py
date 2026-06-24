from sqlalchemy.orm import Session
from app.tasks.models import Task, Priority
import uuid

# BR: Task priority must be one of: low, medium, high, urgent
# BR: Task status transitions: pending → in_progress → completed (one-way)
# BR: Only task owner can modify their tasks
VALID_TRANSITIONS = {"pending": ["in_progress"], "in_progress": ["completed"], "completed": []}

def create_task(db: Session, owner_id: str, title: str, description: str = "", priority: str = "medium") -> Task:
    task = Task(id=str(uuid.uuid4()), title=title, description=description,
                priority=Priority(priority), owner_id=owner_id)
    db.add(task)
    db.commit()
    return task

def update_task_status(db: Session, task_id: str, owner_id: str, new_status: str) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ValueError("Task not found")
    if task.owner_id != owner_id:
        raise ValueError("Not authorized")
    if new_status not in VALID_TRANSITIONS.get(task.status, []):
        raise ValueError(f"Cannot transition from {task.status} to {new_status}")
    task.status = new_status
    db.commit()
    return task

def list_tasks(db: Session, owner_id: str):
    return db.query(Task).filter(Task.owner_id == owner_id).all()
