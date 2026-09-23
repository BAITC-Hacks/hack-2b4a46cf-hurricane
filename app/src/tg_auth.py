"""Login via Telegram Login Widget: signature check, user upsert, bearer session tokens.

Flow: widget on the frontend -> POST /auth/telegram -> JWT in response body ->
frontend sends `Authorization: Bearer <token>` -> `get_current_user` on protected routes.
"""

import hashlib
import hmac
import time
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db import get_session
from src.errors import AppError
from src.models import User
from src.schemas import SessionOut, TelegramAuthIn, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
AUTH_TTL_SECONDS = 24 * 60 * 60
JWT_ALGORITHM = "HS256"


def is_valid_telegram_hash(payload: TelegramAuthIn) -> bool:
    """Telegram signs the fields with sha256(bot_token) as the HMAC key."""
    fields = payload.model_dump(exclude={"hash"}, exclude_none=True)
    check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret = hashlib.sha256(settings.tg_bot_token.encode()).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, payload.hash)


def create_session_token(user: User) -> str:
    expires_at = datetime.now(UTC) + timedelta(days=settings.session_ttl_days)
    claims = {"sub": str(user.id), "exp": expires_at}
    return jwt.encode(claims, settings.secret_key, algorithm=JWT_ALGORITHM)


def read_user_id_from_token(token: str) -> int:
    try:
        claims = jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as error:
        raise AppError("Session is invalid or expired", status_code=401) from error
    return int(claims["sub"])


async def get_or_create_user(session: AsyncSession, payload: TelegramAuthIn) -> User:
    user = await session.scalar(select(User).where(User.tg_id == payload.id))
    if user is None:
        user = User(tg_id=payload.id)
        session.add(user)
    user.username = payload.username
    user.first_name = payload.first_name
    await session.commit()
    return user


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Dependency for protected routes: `user: Annotated[User, Depends(get_current_user)]`."""
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError("Login required", status_code=401)
    user_id = read_user_id_from_token(authorization.removeprefix("Bearer "))
    user = await session.get(User, user_id)
    if user is None:
        raise AppError("Login required", status_code=401)
    return user


@router.post("/telegram", response_model=SessionOut)
async def login_with_telegram(
    payload: TelegramAuthIn, session: Annotated[AsyncSession, Depends(get_session)]
) -> SessionOut:
    if not settings.tg_bot_token:
        raise AppError("Telegram login is not configured", status_code=503)
    if not is_valid_telegram_hash(payload):
        raise AppError("Invalid Telegram signature", status_code=401)
    if time.time() - payload.auth_date > AUTH_TTL_SECONDS:
        raise AppError("Telegram login expired, try again", status_code=401)
    user = await get_or_create_user(session, payload)
    return SessionOut(token=create_session_token(user), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def get_me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user
