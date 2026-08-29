"""Playground service — create, authenticate, and look up playgrounds."""

import secrets
import string

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import SHARE_CODE_LENGTH
from app.models.playground import Playground
from app.utils.sanitize import sanitize_player_names, sanitize_text

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
        pin_hint: str | None = None,
    ) -> Playground:
        share_code = _generate_share_code()
        pin_hash = _hash_pin(pin)

        playground = Playground(
            name=sanitize_text(name),
            pin_hash=pin_hash,
            share_code=share_code,
            players=sanitize_player_names(players),
            pin_hint=sanitize_text(pin_hint) if pin_hint else None,
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
        result = await db.execute(select(Playground).where(Playground.share_code == share_code))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_name(db: AsyncSession, name: str) -> Playground | None:
        result = await db.execute(select(Playground).where(Playground.name == name))
        return result.scalar_one_or_none()

    @staticmethod
    async def delete(db: AsyncSession, playground: Playground) -> None:
        """Delete a playground and all its games and rounds."""
        from app.models.game import Game
        from app.models.round import Round

        game_ids_result = await db.execute(
            select(Game.id).where(Game.playground_id == playground.id)
        )
        game_ids = [row[0] for row in game_ids_result.all()]
        if game_ids:
            from sqlalchemy import delete

            await db.execute(delete(Round).where(Round.game_id.in_(game_ids)))
            await db.execute(delete(Game).where(Game.id.in_(game_ids)))
        await db.delete(playground)
        await db.commit()

    @staticmethod
    async def list_all(db: AsyncSession) -> list[dict]:
        """Return all playgrounds sorted alphabetically. Includes players for filtering."""
        result = await db.execute(
            select(Playground.name, Playground.share_code, Playground.players).order_by(
                Playground.name
            )
        )
        return [{"name": row[0], "share_code": row[1], "players": row[2]} for row in result.all()]

    @staticmethod
    async def list_recent_names(db: AsyncSession, limit: int = 5) -> list[str]:
        result = await db.execute(
            select(Playground.name).order_by(Playground.updated_at.desc()).limit(limit)
        )
        return [row[0] for row in result.all()]
