"""Playground service — create, authenticate, and look up playgrounds."""

import secrets
import string

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.playground import Playground

SHARE_CODE_LENGTH = 8
SHARE_CODE_ALPHABET = string.ascii_uppercase + string.digits


def _generate_share_code() -> str:
    return "".join(secrets.choice(SHARE_CODE_ALPHABET) for _ in range(SHARE_CODE_LENGTH))


def _hash_pin(pin: str) -> str:
    return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()


class PlaygroundService:

    @staticmethod
    async def create(
        db: AsyncSession,
        name: str,
        pin: str,
        players: list[str],
    ) -> Playground:
        share_code = _generate_share_code()
        pin_hash = _hash_pin(pin)

        playground = Playground(
            name=name,
            pin_hash=pin_hash,
            share_code=share_code,
            players=players,
        )
        db.add(playground)
        await db.commit()
        await db.refresh(playground)
        return playground

    @staticmethod
    def verify_pin(playground: Playground, pin: str) -> bool:
        return bcrypt.checkpw(pin.encode(), playground.pin_hash.encode())

    @staticmethod
    async def get_by_share_code(db: AsyncSession, share_code: str) -> Playground | None:
        result = await db.execute(
            select(Playground).where(Playground.share_code == share_code)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_name(db: AsyncSession, name: str) -> Playground | None:
        result = await db.execute(
            select(Playground).where(Playground.name == name)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_recent_names(db: AsyncSession, limit: int = 5) -> list[str]:
        result = await db.execute(
            select(Playground.name)
            .order_by(Playground.updated_at.desc())
            .limit(limit)
        )
        return [row[0] for row in result.all()]
