from __future__ import annotations

import bcrypt
from sqlalchemy import select

from .database import SessionLocal
from .models import Role, User


def authenticate(username: str, password: str) -> User | None:
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.username == username.strip()))
        if not user or not user.is_active:
            return None
    try:
        if not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
            return None
    except ValueError:
        return None
    return user


def register(full_name: str, username: str, password: str) -> tuple[bool, str]:
    return False, "Саморегистрация закрыта. Обратитесь к администратору кафедры для получения учётной записи."


def role_name(user: User) -> str:
    with SessionLocal() as session:
        role = session.get(Role, user.role_id)
        return role.role_name if role else "editor"
