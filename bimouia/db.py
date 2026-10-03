"""Accès MariaDB : pool de connexions, création du schéma et requêtes communes."""

import asyncio
import logging
import warnings
from pathlib import Path
from typing import Any

import aiomysql

from .config import Config

log = logging.getLogger(__name__)

# Avertissements MariaDB attendus (« table déjà existante », INSERT IGNORE) : inutiles dans les logs
warnings.filterwarnings("ignore", category=aiomysql.Warning)

SCHEMA_FILE = Path(__file__).with_name("schema.sql")

# Ligne témoin : la plateforme a déjà été lue une première fois
INIT_MARKER = "__init__"


class Database:
    def __init__(self, pool: aiomysql.Pool) -> None:
        self._pool = pool

    @classmethod
    async def connect(cls, config: Config, attempts: int = 10, delay: float = 3.0) -> "Database":
        # Plusieurs essais : MariaDB peut démarrer après le bot
        for attempt in range(1, attempts + 1):
            try:
                pool = await aiomysql.create_pool(
                    host=config.db_host,
                    port=config.db_port,
                    user=config.db_user,
                    password=config.db_password,
                    db=config.db_name,
                    charset="utf8mb4",
                    autocommit=True,
                    minsize=1,
                    maxsize=5,
                    pool_recycle=3600,
                )
                break
            except Exception as exc:
                if attempt == attempts:
                    raise
                log.warning("MariaDB injoignable (essai %d/%d) : %s", attempt, attempts, exc)
                await asyncio.sleep(delay)
        db = cls(pool)
        await db._create_schema()
        return db

    async def close(self) -> None:
        self._pool.close()
        await self._pool.wait_closed()

    async def _create_schema(self) -> None:
        statements = [s.strip() for s in SCHEMA_FILE.read_text(encoding="utf-8").split(";")]
        for statement in filter(None, statements):
            await self.execute(statement)

    async def execute(self, query: str, args: Any = None) -> int:
        """Exécute une requête et renvoie le nombre de lignes touchées."""
        async with self._pool.acquire() as conn, conn.cursor() as cur:
            return await cur.execute(query, args)

    async def fetchall(self, query: str, args: Any = None) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn, conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(query, args)
            return list(await cur.fetchall())

    async def fetchone(self, query: str, args: Any = None) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn, conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(query, args)
            return await cur.fetchone()

    # --- Notifications déjà envoyées ---

    async def is_sent(self, platform: str, content_id: str) -> bool:
        row = await self.fetchone(
            "SELECT 1 FROM sent_notifications WHERE platform = %s AND content_id = %s",
            (platform, content_id),
        )
        return row is not None

    async def mark_sent(self, platform: str, content_id: str) -> None:
        await self.execute(
            "INSERT IGNORE INTO sent_notifications (platform, content_id) VALUES (%s, %s)",
            (platform, content_id),
        )

    async def is_initialized(self, platform: str) -> bool:
        return await self.is_sent(platform, INIT_MARKER)

    async def mark_initialized(self, platform: str) -> None:
        await self.mark_sent(platform, INIT_MARKER)
