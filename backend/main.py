from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from utils import calculate_age
import models
import schemas

# Creeaza tabelele daca nu exista
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tandem API")

MIN_AGE = 18


@app.get("/")
def home():
    return {"message": "Merge backend-ul!"}


# ---------- AUTH ----------

@app.post("/auth/register", response_model=schemas.UserOut, status_code=201)
def register(data: schemas.UserCreate, db: Session = Depends(get_db)):
    email = data.email.lower()

    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=400, detail="Exista deja un cont cu acest email")

    if calculate_age(data.birth_date) < MIN_AGE:
        raise HTTPException(status_code=400, detail="Trebuie sa ai minim 18 ani")

    user = models.User(
        email=email,
        password_hash=hash_password(data.password),
        name=data.name,
        birth_date=data.birth_date,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=schemas.Token)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    # Formularul standard OAuth2 numeste campul "username"; la noi e emailul.
    user = db.query(models.User).filter(models.User.email == form.username.lower()).first()

    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email sau parola gresita",
        )

    return schemas.Token(access_token=create_access_token(user.id))


@app.get("/me", response_model=schemas.UserOut)
def read_me(current_user: models.User = Depends(get_current_user)):
    return current_user


# ---------- EVENTS ----------

@app.get("/events", response_model=list[schemas.EventOut])
def list_events(db: Session = Depends(get_db)):
    return db.query(models.Event).order_by(models.Event.starts_at).all()


@app.get("/events/{event_id}", response_model=schemas.EventOut)
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Evenimentul nu exista")
    return event