from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, func
from app.database import Base
import enum

class Priority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class Task(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, default="")
    priority = Column(Enum(Priority), default=Priority.MEDIUM)
    status = Column(String, default="pending")  # pending → in_progress → completed
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
