from __future__ import annotations

from pydantic import BaseModel, Field


class AdminStatsResponse(BaseModel):
    total_users: int
    total_calculations: int
    total_gold_value_calculated: float


class UpdateUserRoleRequest(BaseModel):
    role: str = Field(pattern=r"^(user|admin)$")


class UserRoleResponse(BaseModel):
    id: str
    email: str
    role: str
