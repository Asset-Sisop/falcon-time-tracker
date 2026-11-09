from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

def utcnow():
    return datetime.now(timezone.utc)

class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    sessions: Mapped[list["WorkSession"]] = relationship(back_populates="employee", cascade="all, delete-orphan")

class WorkSession(Base):
    __tablename__ = "work_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    task: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    employee: Mapped[Employee] = relationship(back_populates="sessions")
    __table_args__ = (
        Index("ix_work_sessions_employee_started", "employee_id", "started_at"),
        Index("ix_work_sessions_stopped_at", "stopped_at"),
        Index("uq_active_session_per_employee", "employee_id", unique=True,
              postgresql_where=stopped_at.is_(None), sqlite_where=stopped_at.is_(None)),
    )
