from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EventOut(BaseModel):
    """Ce vede frontend-ul cand cere un eveniment."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    category: str
    venue: str
    city: str
    starts_at: datetime
    description: str | None = None
    image_url: str | None = None