from datetime import datetime, timezone
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from .database import Base, engine, get_db
from .models import Employee, WorkSession, utcnow
from .schemas import EmployeeCreate, EmployeeRead, TimerStart, SessionRead, ReportRow

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Falcon Time Tracker", version="1.0.0",
              description="Employee time tracking demo built for the Falcon AI programming assignment.")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
def index():
    return FileResponse("static/index.html")

def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

def session_out(item: WorkSession) -> SessionRead:
    return SessionRead(
        id=item.id, employee_id=item.employee_id, employee_name=item.employee.name,
        task=item.task, description=item.description, started_at=item.started_at,
        stopped_at=item.stopped_at, duration_seconds=item.duration_seconds,
        is_running=item.stopped_at is None
    )

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/employees", response_model=EmployeeRead, status_code=201)
def create_employee(payload: EmployeeCreate, db: Annotated[Session, Depends(get_db)]):
    employee = Employee(name=payload.name.strip(), email=str(payload.email).lower() if payload.email else None)
    if not employee.name:
        raise HTTPException(422, "Employee name cannot be blank")
    db.add(employee)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        if "unique" in str(exc).lower():
            raise HTTPException(409, "An employee with this email already exists") from exc
        raise
    db.refresh(employee)
    return employee

@app.get("/api/employees", response_model=list[EmployeeRead])
def list_employees(db: Annotated[Session, Depends(get_db)]):
    return db.scalars(select(Employee).order_by(Employee.name)).all()

@app.delete("/api/employees/{employee_id}", status_code=204)
def delete_employee(employee_id: int, db: Annotated[Session, Depends(get_db)]):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(404, "Employee not found")
    db.delete(employee)
    db.commit()

@app.post("/api/employees/{employee_id}/timer/start", response_model=SessionRead, status_code=201)
def start_timer(employee_id: int, payload: TimerStart, db: Annotated[Session, Depends(get_db)]):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(404, "Employee not found")
    active = db.scalar(select(WorkSession).where(
        WorkSession.employee_id == employee_id, WorkSession.stopped_at.is_(None)
    ))
    if active:
        raise HTTPException(409, "This employee already has an active timer")
    task = payload.task.strip()
    if not task:
        raise HTTPException(422, "Task cannot be blank")
    item = WorkSession(employee_id=employee_id, task=task,
                       description=payload.description.strip() if payload.description else None,
                       started_at=utcnow())
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "This employee already has an active timer") from exc
    db.refresh(item)
    return session_out(item)

@app.post("/api/sessions/{session_id}/stop", response_model=SessionRead)
def stop_timer(session_id: int, db: Annotated[Session, Depends(get_db)]):
    item = db.scalar(select(WorkSession).options(joinedload(WorkSession.employee)).where(WorkSession.id == session_id))
    if not item:
        raise HTTPException(404, "Session not found")
    if item.stopped_at is not None:
        raise HTTPException(409, "Timer has already been stopped")
    stopped = utcnow()
    item.stopped_at = stopped
    item.duration_seconds = max(0, int((as_utc(stopped) - as_utc(item.started_at)).total_seconds()))
    db.commit()
    db.refresh(item)
    return session_out(item)

@app.get("/api/sessions", response_model=list[SessionRead])
def list_sessions(
    db: Annotated[Session, Depends(get_db)],
    employee_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    # Filter by session start timestamp; date_to is inclusive by calendar day when supplied as YYYY-MM-DD.
    stmt = select(WorkSession).options(joinedload(WorkSession.employee)).order_by(WorkSession.started_at.desc())
    if employee_id is not None:
        stmt = stmt.where(WorkSession.employee_id == employee_id)
    if date_from is not None:
        stmt = stmt.where(WorkSession.started_at >= as_utc(date_from))
    if date_to is not None:
        end = as_utc(date_to)
        if len(str(date_to)) <= 10:
            end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
        stmt = stmt.where(WorkSession.started_at <= end)
    return [session_out(x) for x in db.scalars(stmt).unique().all()]

@app.get("/api/reports", response_model=list[ReportRow])
def report(
    db: Annotated[Session, Depends(get_db)],
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
):
    start, end = as_utc(date_from), as_utc(date_to)
    if end < start:
        raise HTTPException(422, "date_to must be on or after date_from")
    # Report duration is clipped to the selected period, including currently running sessions.
    now = utcnow()
    employees = db.scalars(select(Employee).order_by(Employee.name)).all()
    sessions = db.scalars(select(WorkSession).options(joinedload(WorkSession.employee))
        .where(WorkSession.started_at <= end)).unique().all()
    totals: dict[int, tuple[int, int]] = {e.id: (0, 0) for e in employees}
    for item in sessions:
        session_start = as_utc(item.started_at)
        session_end = as_utc(item.stopped_at) if item.stopped_at else now
        overlap_start, overlap_end = max(session_start, start), min(session_end, end)
        seconds = max(0, int((overlap_end - overlap_start).total_seconds()))
        if seconds > 0 or (start <= session_start <= end):
            old_seconds, old_count = totals.get(item.employee_id, (0, 0))
            totals[item.employee_id] = (old_seconds + seconds, old_count + 1)
    return [ReportRow(employee_id=e.id, employee_name=e.name,
                      total_seconds=totals[e.id][0], sessions_count=totals[e.id][1])
            for e in employees]

@app.get("/api/summary")
def summary(db: Annotated[Session, Depends(get_db)]):
    employees = db.scalar(select(func.count(Employee.id))) or 0
    active = db.scalar(select(func.count(WorkSession.id)).where(WorkSession.stopped_at.is_(None))) or 0
    return {"employees": employees, "active_timers": active}
