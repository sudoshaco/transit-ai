from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Location(BaseModel):
    type: str = "station"
    id: Optional[str] = None
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    model_config = {"extra": "allow"}


class Stop(BaseModel):
    station: Optional[Location] = None
    arrival: Optional[str] = None
    departure: Optional[str] = None
    delay: Optional[int] = None
    platform: Optional[str] = None

    model_config = {"extra": "allow"}


class Price(BaseModel):
    amount: Optional[float] = None
    currency: Optional[str] = "EUR"
    hint: Optional[str] = None

    model_config = {"extra": "allow"}


class Remark(BaseModel):
    type: Optional[str] = None
    code: Optional[str] = None
    text: Optional[str] = None

    model_config = {"extra": "allow"}


class Route(BaseModel):
    duration_minutes: int = 0
    transfers: int = 0
    departure: Optional[str] = None
    arrival: Optional[str] = None
    legs: list = []
    price: Optional[Price] = None
    remarks: Optional[list[Remark]] = []

    model_config = {"extra": "allow"}
