from datetime import date

from database import Base, engine, SessionLocal
from security import hash_password
import models

Base.metadata.create_all(bind=engine)
db = SessionLocal()

DEMO_USERS = [
    ("ana@demo.ro", "Ana", date(2004, 3, 12), "Student la Litere, iubesc teatrul."),
    ("bogdan@demo.ro", "Bogdan", date(2003, 9, 1), "Merg la concerte de jazz."),
    ("cristina@demo.ro", "Cristina", date(2005, 6, 20), "Nou in Timisoara, caut companie."),
    ("dan@demo.ro", "Dan", date(1990, 1, 5), "Pasionat de opera."),
]

event = db.query(models.Event).order_by(models.Event.id).first()

for email, name, birth, bio in DEMO_USERS:
    user = db.query(models.User).filter_by(email=email).first()
    if user is None:
        user = models.User(
            email=email,
            password_hash=hash_password("parola1234"),
            name=name,
            birth_date=birth,
            bio=bio,
            verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    if event is not None:
        exists = db.query(models.EventInterest).filter_by(
            user_id=user.id, event_id=event.id
        ).first()
        if exists is None:
            db.add(models.EventInterest(user_id=user.id, event_id=event.id))
            db.commit()

print("Useri demo creati. Parola pentru toti: parola1234")
db.close()