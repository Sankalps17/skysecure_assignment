"""Pydantic models for Zoho Projects API responses."""

from pydantic import BaseModel


class ZohoTokens(BaseModel):
    """OAuth token set returned by Zoho's token endpoint."""
    access_token: str
    refresh_token: str
    expires_at: float  # Unix timestamp — token invalid after this


class Portal(BaseModel):
    """A Zoho Projects portal (top-level organization)."""
    id: str
    name: str


class Project(BaseModel):
    """A project within a portal."""
    id: str
    name: str
    status: str
    owner_name: str = ""
    task_count_open: int = 0
    task_count_closed: int = 0


class TaskOwner(BaseModel):
    """A user assigned to a task."""
    id: str
    name: str


class TaskStatus(BaseModel):
    """Status metadata for a task."""
    name: str
    id: str
    color_code: str = ""


class Task(BaseModel):
    """A task within a project."""
    id: str
    name: str
    status: TaskStatus
    priority: str = "None"
    start_date: str = ""
    end_date: str = ""
    owners: list[TaskOwner] = []
    percent_complete: str = "0"


class User(BaseModel):
    """A team member in a project."""
    id: str
    name: str
    email: str = ""
    role: str = ""


class TimeLog(BaseModel):
    """A single time-tracking entry."""
    id: str
    task_name: str
    owner_name: str
    owner_id: str
    hours: str
    notes: str = ""
    date: str = ""


class Milestone(BaseModel):
    """A milestone within a project."""
    id: str
    name: str
    status: str = ""
    owner_name: str = ""
    start_date: str = ""
    end_date: str = ""
    completed_date: str = ""
