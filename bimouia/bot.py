"""Client Discord BimouIA : connexion, chargement des modules et synchronisation des commandes."""

import logging

import aiohttp
import discord
from discord.ext import commands

from .config import Config
from .db import Database
from .ui import reply_error

log = logging.getLogger(__name__)

EXTENSIONS = ("bimouia.cogs.reaction_roles", "bimouia.cogs.notifications")


class BimouIA(commands.Bot):
    def __init__(self, config: Config) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned,  # uniquement des commandes slash
            intents=discord.Intents.default(),
            allowed_mentions=discord.AllowedMentions.none(),  # aucune mention par défaut
            help_command=None,
        )
        self.config = config
        self.db: Database
        self.http_session: aiohttp.ClientSession

    async def setup_hook(self) -> None:
        self.http_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        self.db = await Database.connect(self.config)
        self.tree.error(reply_error)
        for extension in EXTENSIONS:
            await self.load_extension(extension)
        # Bot privé : commandes enregistrées sur le serveur uniquement (disponibles immédiatement)
        guild = discord.Object(id=self.config.guild_id)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        log.info("%d commande(s) synchronisée(s)", len(synced))

    async def on_ready(self) -> None:
        log.info("Connecté en tant que %s", self.user)

    async def close(self) -> None:
        await super().close()
        if hasattr(self, "http_session"):
            await self.http_session.close()
        if hasattr(self, "db"):
            await self.db.close()
