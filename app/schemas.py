from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, EmailStr

class EmployeeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr | None = None

class EmployeeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str | None
    created_at: datetime

class TimerStart(BaseModel):
    task: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)

class SessionRead(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    task: str
    description: str | None
    started_at: datetime
    stopped_at: datetime | None
    duration_seconds: int | None
    is_running: bool

class ReportRow(BaseModel):
    employee_id: int
    employee_name: str
    total_seconds: int
    sessions_count: int
