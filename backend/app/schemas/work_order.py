"""Schemas: work orders."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, Field


class WorkOrder(BaseModel):
    id: str
    seq: int
    wo_number: str
    asset_code: str
    equipment_type: str
    status_unit: str
    priority: str
    component: str
    part_no: Optional[str] = None
    rul_hours: int
    est_cost: int
    scheduled_at: Optional[datetime] = None
    est_completion_at: Optional[datetime] = None
    technician: Optional[str] = None
    notes: Optional[str] = None
    feedback: Optional[str] = None
    wo_status: str
    created_at: datetime
    updated_at: datetime


class CreateWorkOrderRequest(BaseModel):
    asset_code: Annotated[str, Field(min_length=1, max_length=80)]
    equipment_type: Optional[str] = None
    status_unit: str
    priority: Optional[str] = None
    component: Optional[str] = None
    part_no: Optional[str] = None
    rul_hours: Optional[int] = None
    est_cost: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    est_completion_at: Optional[datetime] = None
    technician: Optional[str] = None
    notes: Optional[str] = None


class UpdateWorkOrderRequest(BaseModel):
    wo_status: Optional[str] = None
    technician: Optional[str] = None
    notes: Optional[str] = None
    feedback: Optional[str] = None


class WorkOrderListQuery(BaseModel):
    page: Optional[int] = None
    per_page: Optional[int] = None
    wo_status: Optional[str] = None
    asset_code: Optional[str] = None
