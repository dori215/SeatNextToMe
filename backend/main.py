from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from database import Base, engine, get_db
import models
import schemas

# Creeaza tabelele daca nu exista
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tandem API")


@app.get("/")
def home():
    return {"message": "Merge backend-ul!"}


@app.get("/events", response_model=list[schemas.EventOut])
def list_events(db: Session = Depends(get_db)):
    return db.query(models.Event).order_by(models.Event.starts_at).all()


@app.get("/events/{event_id}", response_model=schemas.EventOut)
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Evenimentul nu exista")
    return event