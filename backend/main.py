from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_, and_

from fastapi import WebSocket, WebSocketDisconnect, Query
from database import SessionLocal
from security import get_user_from_token
from ws_manager import manager

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite
        "http://127.0.0.1:5173",
        "http://localhost:3000",   # alte setup-uri React
        "http://localhost:8081",
        "http://127.0.0.1:8081",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MIN_AGE = 18

def to_public_user(user: models.User) -> dict:
    # Expunem DOAR ce e sigur: fără email, fără data nașterii
    return {
        "id": user.id,
        "name": user.name,
        "age": calculate_age(user.birth_date),
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "verified": user.verified,
    }


def to_connection_out(conn: models.Connection, me: models.User, db: Session) -> dict:
    # Aflăm cine e "celălalt" din conexiune
    other_id = conn.addressee_id if conn.requester_id == me.id else conn.requester_id
    other = db.get(models.User, other_id)
    return {
        "id": conn.id,
        "status": conn.status,
        "event_id": conn.event_id,
        "user": to_public_user(other),
    }


def find_connection(db: Session, user_a: int, user_b: int):
    # Caută o conexiune între doi useri, în orice direcție
    return db.query(models.Connection).filter(
        or_(
            and_(models.Connection.requester_id == user_a,
                 models.Connection.addressee_id == user_b),
            and_(models.Connection.requester_id == user_b,
                 models.Connection.addressee_id == user_a),
        )
    ).first()

def create_chat_for_connection(db: Session, conn: models.Connection) -> models.Chat:
    existing = db.query(models.Chat).filter(models.Chat.connection_id == conn.id).first()
    if existing:
        return existing

    chat = models.Chat(connection_id=conn.id, event_id=conn.event_id)
    db.add(chat)
    db.flush()   # trimite INSERT-ul ca să primim chat.id, dar fără commit încă

    db.add_all([
        models.ChatMember(chat_id=chat.id, user_id=conn.requester_id),
        models.ChatMember(chat_id=chat.id, user_id=conn.addressee_id),
    ])
    db.commit()
    return chat

def is_chat_member(db: Session, chat_id: int, user_id: int) -> bool:
    return db.query(models.ChatMember).filter(
        models.ChatMember.chat_id == chat_id,
        models.ChatMember.user_id == user_id,
    ).first() is not None
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

@app.post("/connections", response_model=schemas.ConnectionOut, status_code=201)
def send_connection_request(
    data: schemas.ConnectionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if data.addressee_id == current_user.id:
        raise HTTPException(status_code=400, detail="Nu îți poți trimite cerere singur")

    other = db.get(models.User, data.addressee_id)
    if other is None:
        raise HTTPException(status_code=404, detail="Userul nu există")

    # Regula de siguranță: doar persoane cu vârstă compatibilă
    diff = abs(calculate_age(current_user.birth_date) - calculate_age(other.birth_date))
    if diff > AGE_RANGE:
        raise HTTPException(status_code=403, detail="Diferența de vârstă este prea mare")

    existing = find_connection(db, current_user.id, other.id)
    if existing:
        # Celălalt ne-a trimis deja o cerere -> amândoi vor, acceptăm automat
        if existing.status == "pending" and existing.requester_id == other.id:
            existing.status = "accepted"
            db.commit()
            db.refresh(existing)
            create_chat_for_connection(db, existing)
            return to_connection_out(existing, current_user, db)
        raise HTTPException(status_code=400, detail="Există deja o conexiune sau o cerere între voi")

    conn = models.Connection(
        requester_id=current_user.id,
        addressee_id=other.id,
        event_id=data.event_id,
        status="pending",
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return to_connection_out(conn, current_user, db)


@app.get("/connections/requests", response_model=list[schemas.ConnectionOut])
def incoming_requests(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Cererile primite, încă neacceptate."""
    conns = db.query(models.Connection).filter(
        models.Connection.addressee_id == current_user.id,
        models.Connection.status == "pending",
    ).all()
    return [to_connection_out(c, current_user, db) for c in conns]


@app.get("/connections", response_model=list[schemas.ConnectionOut])
def my_connections(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Conexiunile acceptate (prietenii mei)."""
    conns = db.query(models.Connection).filter(
        or_(models.Connection.requester_id == current_user.id,
            models.Connection.addressee_id == current_user.id),
        models.Connection.status == "accepted",
    ).all()
    return [to_connection_out(c, current_user, db) for c in conns]


def get_pending_request_for_me(db: Session, connection_id: int, me: models.User) -> models.Connection:
    conn = db.get(models.Connection, connection_id)
    # Doar destinatarul poate accepta/refuza, și doar cât timp e pending
    if conn is None or conn.addressee_id != me.id:
        raise HTTPException(status_code=404, detail="Cererea nu există")
    if conn.status != "pending":
        raise HTTPException(status_code=400, detail="Cererea a fost deja procesată")
    return conn


@app.post("/connections/{connection_id}/accept", response_model=schemas.ConnectionOut)
def accept_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    conn = get_pending_request_for_me(db, connection_id, current_user)
    conn.status = "accepted"
    db.commit()
    db.refresh(conn)
    create_chat_for_connection(db, conn)
    return to_connection_out(conn, current_user, db)


@app.post("/connections/{connection_id}/decline", response_model=schemas.ConnectionOut)
def decline_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    conn = get_pending_request_for_me(db, connection_id, current_user)
    conn.status = "declined"
    db.commit()
    db.refresh(conn)
    return to_connection_out(conn, current_user, db)

@app.websocket("/ws/chat/{chat_id}")
async def chat_websocket(websocket: WebSocket, chat_id: int, token: str = Query(...)):
    # 1. Autentificare și verificare că userul e membru (sesiune DB scurtă)
    with SessionLocal() as db:
        user = get_user_from_token(token, db)
        if user is None or not is_chat_member(db, chat_id, user.id):
            await websocket.close(code=1008)   # 1008 = "policy violation"
            return
        user_id = user.id

    # 2. Intrăm în cameră
    await manager.connect(chat_id, websocket)

    try:
        while True:
            text = (await websocket.receive_text()).strip()   # așteptăm un mesaj
            if not text or len(text) > 1000:
                continue                                       # ignorăm mesajele goale/prea lungi

            # 3. Salvăm în baza de date (sesiune scurtă, nu ținem una deschisă tot chatul)
            with SessionLocal() as db:
                msg = models.Message(chat_id=chat_id, sender_id=user_id, content=text)
                db.add(msg)
                db.commit()
                db.refresh(msg)
                payload = {
                    "id": msg.id,
                    "chat_id": chat_id,
                    "sender_id": user_id,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                }

            # 4. Trimitem tuturor din cameră (inclusiv expeditorului, ca să vadă confirmarea)
            await manager.broadcast(chat_id, payload)

    except WebSocketDisconnect:
        manager.disconnect(chat_id, websocket)


@app.get("/chats", response_model=list[schemas.ChatOut])
def my_chats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    memberships = db.query(models.ChatMember).filter(
        models.ChatMember.user_id == current_user.id
    ).all()

    result = []
    for m in memberships:
        chat = db.get(models.Chat, m.chat_id)
        # Celălalt membru al chatului 1:1
        other_member = db.query(models.ChatMember).filter(
            models.ChatMember.chat_id == chat.id,
            models.ChatMember.user_id != current_user.id,
        ).first()
        other = db.get(models.User, other_member.user_id)
        last = db.query(models.Message).filter(
            models.Message.chat_id == chat.id
        ).order_by(models.Message.id.desc()).first()

        result.append({
            "id": chat.id,
            "event_id": chat.event_id,
            "other_user": to_public_user(other),
            "last_message": last,
        })
    return result


@app.get("/chats/{chat_id}/messages", response_model=list[schemas.MessageOut])
def chat_history(
    chat_id: int,
    limit: int = Query(50, ge=1, le=200),
    before_id: int | None = None,      # pentru "încarcă mai vechi"
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not is_chat_member(db, chat_id, current_user.id):
        raise HTTPException(status_code=404, detail="Chatul nu există")

    q = db.query(models.Message).filter(models.Message.chat_id == chat_id)
    if before_id is not None:
        q = q.filter(models.Message.id < before_id)

    messages = q.order_by(models.Message.id.desc()).limit(limit).all()
    return list(reversed(messages))   # le returnăm de la cel mai vechi la cel mai nou


@app.post("/chats/{chat_id}/messages", response_model=schemas.MessageOut, status_code=201)
async def send_message_http(
    chat_id: int,
    data: schemas.MessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not is_chat_member(db, chat_id, current_user.id):
        raise HTTPException(status_code=404, detail="Chatul nu există")

    msg = models.Message(chat_id=chat_id, sender_id=current_user.id, content=data.content.strip())
    db.add(msg)
    db.commit()
    db.refresh(msg)

    # Îi anunțăm și pe cei conectați prin WebSocket
    await manager.broadcast(chat_id, {
        "id": msg.id,
        "chat_id": chat_id,
        "sender_id": msg.sender_id,
        "content": msg.content,
        "created_at": msg.created_at.isoformat(),
    })
    return msg