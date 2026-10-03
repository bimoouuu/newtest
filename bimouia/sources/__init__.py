"""Sources de notifications : chaque source renvoie les contenus actuellement visibles."""

from typing import Protocol

from ..announcements import Announcement


class SourceNotReady(Exception):
    """La source ne peut pas encore être lue (ex : compte TikTok non connecté)."""


class Source(Protocol):
    platform: str
    interval: int
    # True : au tout premier passage, on enregistre l'existant sans l'annoncer
    seed_on_first_run: bool

    async def fetch(self) -> list[Announcement]:
        """Renvoie les contenus du plus ancien au plus récent."""
        ...
