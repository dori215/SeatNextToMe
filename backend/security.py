import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
import models

# In productie cheia vine din variabila de mediu. Pentru hackathon e ok si asa.
SECRET_KEY = os.getenv("SECRET_KEY", "schimba-cheia-asta-cu-ceva-lung-si-random")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 24  # tokenul e valabil 24 de ore

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """Scoate userul din token. Il folosim in orice endpoint protejat."""
    error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalid sau expirat",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise error

    user = db.get(models.User, user_id)
    if user is None:
        raise error
    return user

def get_user_from_token(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None                      # token invalid sau expirat

    sub = payload.get("sub")
    if sub is None:
        return None

    # La tine "sub" poate fi id-ul sau emailul; acoperim ambele cazuri.
    # (Uită-te în get_current_user ca să vezi ce pui tu în token.)
    if str(sub).isdigit():
        return db.get(models.User, int(sub))
    return db.query(models.User).filter(models.User.email == sub).first()