from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "sqlite:///./tandem.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Toate tabelele noastre mostenesc din clasa asta."""
    pass


def get_db():
    """Deschide o sesiune cu baza pentru un request si o inchide la final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()