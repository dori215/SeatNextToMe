from datetime import datetime

from database import Base, engine, SessionLocal
import models

Base.metadata.create_all(bind=engine)

db = SessionLocal()

if db.query(models.Event).count() == 0:
    events = [
        models.Event(
            title="Concert Filarmonica Banatul",
            category="concert",
            venue="Filarmonica Banatul",
            city="Timisoara",
            starts_at=datetime(2026, 12, 5, 19, 0),
            description="Seara de muzica clasica.",
        ),
        models.Event(
            title="Hamlet",
            category="teatru",
            venue="Teatrul National Timisoara",
            city="Timisoara",
            starts_at=datetime(2026, 12, 12, 19, 30),
            description="Piesa clasica de Shakespeare.",
        ),
        models.Event(
            title="Seara de Jazz",
            category="concert",
            venue="Club Form Space",
            city="Timisoara",
            starts_at=datetime(2026, 12, 18, 21, 0),
            description="Jazz live cu trupe locale.",
        ),
        models.Event(
            title="Opera: La Traviata",
            category="opera",
            venue="Opera Nationala Romana Timisoara",
            city="Timisoara",
            starts_at=datetime(2026, 12, 20, 18, 0),
            description="Opera de Verdi.",
        ),
    ]
    db.add_all(events)
    db.commit()
    print("Am adaugat evenimentele de test.")
else:
    print("Baza are deja evenimente, nu adaug nimic.")

db.close()