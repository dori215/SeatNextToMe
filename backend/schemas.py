from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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


class UserCreate(BaseModel):
    """Ce trimite frontend-ul la inregistrare."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    name: str = Field(min_length=1, max_length=100)
    birth_date: date


class UserOut(BaseModel):
    """Ce primeste frontend-ul inapoi. Fara parola!"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    birth_date: date
    bio: str | None = None
    avatar_url: str | None = None
    verified: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class InterestIn(BaseModel):
    looking_for_company: bool = True


class InterestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: int
    looking_for_company: bool


class PublicUser(BaseModel):
    """Ce vad ceilalti useri despre tine. Fara email, fara data nasterii."""
    id: int
    name: str
    age: int
    bio: str | None = None
    avatar_url: str | None = None
    verified: bool

class PublicUserOut(BaseModel):
    id: int
    name: str
    age: int
    bio: str | None = None
    avatar_url: str | None = None
    verified: bool


class ConnectionCreate(BaseModel):
    addressee_id: int
    event_id: int | None = None   # opțional: la ce eveniment s-au găsit


class ConnectionOut(BaseModel):
    id: int
    status: str
    event_id: int | None = None
    user: PublicUserOut           # "celălalt" user, din perspectiva celui care întreabă

class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # permite citirea direct din obiecte SQLAlchemy

    id: int
    chat_id: int
    sender_id: int
    content: str
    created_at: datetime


class ChatOut(BaseModel):
    id: int
    event_id: int | None = None
    other_user: PublicUserOut
    last_message: MessageOut | None = None