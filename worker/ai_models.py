"""Pydantic model for AI-extracted event data.
Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/ai_models.py)
"""
from typing import List, Optional

from pydantic import BaseModel, Field

class AIEventExtraction(BaseModel):
    title: Optional[str] = None
    start_time: Optional[str] = None   # ISO string
    end_time: Optional[str] = None
    venue_name: Optional[str] = None
    city: Optional[str] = None
    artist_names: List[str] = Field(default_factory=list)
    ticket_link: Optional[str] = None
    rsvp_link: Optional[str] = None
    is_private_rsvp: bool = False
    private_access: dict = Field(default_factory=dict)
    notes: Optional[str] = None
