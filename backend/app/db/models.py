from sqlalchemy import Column, String, JSON, Enum, DateTime, func, Text
from .database import Base
import enum, uuid

class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    AWAITING_INPUT = "AWAITING_INPUT"
    OUTLINING = "OUTLINING"
    DRAFTING = "DRAFTING"
    REFINING = "REFINING"
    DONE = "DONE"
    ERROR = "ERROR"

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    template = Column(String, nullable=False)
    answers = Column(JSON, default=dict)
    outline_md = Column(Text)
    section_map = Column(JSON, default=dict)   # {h1: {text, summary}}
    final_md = Column(Text)
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
