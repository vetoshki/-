from datetime import datetime
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class LoginRequest(BaseModel):
    email: str
    password: str


class TicketCreate(BaseModel):
    description: str = Field(..., min_length=10, max_length=5000)
    contact_info: str = Field(..., max_length=500)


class TicketResponse(BaseModel):
    id: int
    description: str
    contact_info: str
    status_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class RecommendationItem(BaseModel):
    kb_id: int
    rank: int
    similarity: int
    problem: str
    solution: str


class RecommendationsResponse(BaseModel):
    is_novel: bool
    max_similarity: int
    recommendations: List[RecommendationItem]


class ResolveRequest(BaseModel):
    applied_solution: str = Field("", max_length=5000)
    used_kb: bool = False
    accepted_kb_id: Optional[int] = None


class ConfirmRequest(BaseModel):
    is_confirmed: bool


class KnowledgeItemResponse(BaseModel):
    id: int
    problem: str
    solution: str
    frequency: int
    is_auto_generated: bool
    created_at: datetime

    class Config:
        from_attributes = True
