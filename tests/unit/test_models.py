"""Unit tests for ORM model definitions."""

from app.models.round import Round


class TestRoundModel:
    def test_round_has_game_id_index(self):
        """Round table must have an explicit single-column index on game_id."""
        indexes = {idx.name for idx in Round.__table__.indexes}
        assert "ix_round_game_id" in indexes, (
            f"Missing ix_round_game_id index. Found indexes: {indexes}"
        )

    def test_round_game_id_has_cascade_delete(self):
        """L11: Round.game_id FK must have ON DELETE CASCADE."""
        fk = list(Round.__table__.c.game_id.foreign_keys)[0]
        assert fk.ondelete == "CASCADE", (
            f"Round.game_id FK missing ondelete=CASCADE, got: {fk.ondelete}"
        )
