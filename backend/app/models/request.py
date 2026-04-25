from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.route import Route


class RouteRequest(BaseModel):
    query: str
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    budget_eur: Optional[float] = None


class IntentPreferences(BaseModel):
    no_transfers: bool = False
    max_transfers: Optional[int] = None
    cheapest: bool = False
    fastest: bool = False
    accessible: bool = False  # Barrierefrei
    avoid_bus: bool = False

    model_config = {"extra": "allow"}


class UserIntent(BaseModel):
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    budget_eur: Optional[float] = None
    preferences: Optional[dict] = Field(default_factory=dict)
    # Round-trip support
    is_roundtrip: bool = False
    return_departure_time: Optional[datetime] = None


class RouteResponse(BaseModel):
    routes: list[Route] = []
    affordable_routes: list[Route] = []
    over_budget_routes: list[Route] = []
    ai_recommendation: Optional[Route] = None
    ai_explanation: str = ""
    warnings: list[str] = []
    intent: Optional[UserIntent] = None
    budget_eur: Optional[float] = None


class RoundtripResponse(BaseModel):
    outbound: RouteResponse
    return_trip: RouteResponse
    ai_summary: str = ""
    is_roundtrip: bool = True


class ChatOnlyResponse(BaseModel):
    """Returned for non-travel queries like 'ich mag Zuege'."""
    reply: str
    is_chat: bool = True
