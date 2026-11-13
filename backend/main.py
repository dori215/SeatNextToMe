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

# ---------- INTERESE + MATCHING ----------

AGE_RANGE = 3  # diferenta maxima de varsta (in ani) la matching


@app.post("/events/{event_id}/interest", response_model=schemas.InterestOut)
def set_interest(
    event_id: int,
    data: schemas.InterestIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if db.get(models.Event, event_id) is None:
        raise HTTPException(status_code=404, detail="Evenimentul nu exista")

    interest = (
        db.query(models.EventInterest)
        .filter_by(user_id=current_user.id, event_id=event_id)
        .first()
    )

    if interest is None:
        interest = models.EventInterest(
            user_id=current_user.id,
            event_id=event_id,
            looking_for_company=data.looking_for_company,
        )
        db.add(interest)
    else:
        interest.looking_for_company = data.looking_for_company

    db.commit()
    db.refresh(interest)
    return interest


@app.delete("/events/{event_id}/interest", status_code=204)
def remove_interest(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    interest = (
        db.query(models.EventInterest)
        .filter_by(user_id=current_user.id, event_id=event_id)
        .first()
    )
    if interest is not None:
        db.delete(interest)
        db.commit()


@app.get("/events/{event_id}/matches", response_model=list[schemas.PublicUser])
def event_matches(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if db.get(models.Event, event_id) is None:
        raise HTTPException(status_code=404, detail="Evenimentul nu exista")

    # Vezi matches doar daca te-ai expus si tu
    mine = (
        db.query(models.EventInterest)
        .filter_by(user_id=current_user.id, event_id=event_id)
        .first()
    )
    if mine is None or not mine.looking_for_company:
        raise HTTPException(
            status_code=400,
            detail="Marcheaza mai intai ca esti interesat si cauti companie",
        )

    my_age = calculate_age(current_user.birth_date)

    candidates = (
        db.query(models.User)
        .join(models.EventInterest, models.EventInterest.user_id == models.User.id)
        .filter(
            models.EventInterest.event_id == event_id,
            models.EventInterest.looking_for_company.is_(True),
            models.User.id != current_user.id,
        )
        .all()
    )

    matches = []
    for u in candidates:
        age = calculate_age(u.birth_date)
        if abs(age - my_age) <= AGE_RANGE:
            matches.append(
                schemas.PublicUser(
                    id=u.id,
                    name=u.name,
                    age=age,
                    bio=u.bio,
                    avatar_url=u.avatar_url,
                    verified=u.verified,
                )
            )
    return matches