"""Notifications : lives et publications annoncés dans un salon unique, avec la mention @notifs."""

from __future__ import annotations

import asyncio
import io
import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from ..announcements import Announcement, build_embed, build_view
from ..sources import Source, SourceNotReady
from ..sources.tiktok import TikTokAuth, TikTokVideoSource
from ..sources.twitch import TwitchSource
from ..sources.youtube import YouTubeSource
from ..ui import UserError

if TYPE_CHECKING:
    from ..bot import BimouIA

log = logging.getLogger(__name__)

IMAGE_NAME = "apercu.jpg"


class Notifications(commands.Cog):
    live = app_commands.Group(
        name="live",
        description="Annoncer un live",
        guild_only=True,
        default_permissions=discord.Permissions(manage_roles=True),
    )

    def __init__(self, bot: BimouIA) -> None:
        self.bot = bot
        self.sources = self._build_sources()
        self._tasks: list[asyncio.Task[None]] = []

    def _build_sources(self) -> list[Source]:
        cfg, session = self.bot.config, self.bot.http_session
        sources: list[Source] = []
        if cfg.twitch_enabled:
            sources.append(TwitchSource(session, cfg.twitch_client_id, cfg.twitch_client_secret,
                                        cfg.twitch_login, cfg.twitch_interval))
        if cfg.youtube_enabled:
            sources.append(YouTubeSource(session, cfg.youtube_channel_id, cfg.youtube_interval))
        if cfg.tiktok_videos_enabled:
            auth = TikTokAuth(session, self.bot.db, cfg.tiktok_client_key, cfg.tiktok_client_secret,
                              cfg.tiktok_redirect_uri)
            sources.append(TikTokVideoSource(session, auth, cfg.tiktok_interval))
        return sources

    async def cog_load(self) -> None:
        for source in self.sources:
            self._tasks.append(asyncio.create_task(self._watch(source), name=f"notif-{source.platform}"))
            log.info("Surveillance %s active (toutes les %d s)", source.platform, source.interval)

    async def cog_unload(self) -> None:
        for task in self._tasks:
            task.cancel()

    # --- Surveillance automatique ---

    async def _watch(self, source: Source) -> None:
        await self.bot.wait_until_ready()
        warned = False
        while True:
            try:
                await self._poll(source)
                warned = False
            except SourceNotReady as exc:
                # Message affiché une seule fois tant que la situation ne change pas
                if not warned:
                    log.warning("%s : %s", source.platform, exc)
                    warned = True
            except Exception:
                log.exception("Lecture %s impossible", source.platform)
            await asyncio.sleep(source.interval)

    async def _poll(self, source: Source) -> None:
        db = self.bot.db
        items = await source.fetch()
        if source.seed_on_first_run and not await db.is_initialized(source.platform):
            # Premier passage : on enregistre l'existant sans inonder le salon d'anciennes publications
            for item in items:
                await db.mark_sent(item.platform, item.content_id)
            await db.mark_initialized(source.platform)
            log.info("%s : %d contenu(s) existant(s) enregistré(s) sans annonce", source.platform, len(items))
            return
        for item in items:
            if not await db.is_sent(item.platform, item.content_id):
                await self.announce(item)
                await db.mark_sent(item.platform, item.content_id)

    # --- Envoi ---

    async def announce(self, item: Announcement) -> None:
        cfg = self.bot.config
        channel = self.bot.get_channel(cfg.notif_channel_id) or await self.bot.fetch_channel(cfg.notif_channel_id)
        file = await self._download_image(item.image_url) if item.attach_image and item.image_url else None
        kwargs = {
            "content": f"<@&{cfg.notif_role_id}> {item.headline}",
            "embed": build_embed(item, f"attachment://{IMAGE_NAME}" if file else None),
            "view": build_view(item),
            # Seul le rôle @notifs peut être mentionné
            "allowed_mentions": discord.AllowedMentions(everyone=False, users=False,
                                                        roles=[discord.Object(cfg.notif_role_id)]),
        }
        if file:
            kwargs["file"] = file
        await channel.send(**kwargs)
        log.info("Annonce %s envoyée : %s", item.platform, item.title)

    async def _download_image(self, url: str) -> discord.File | None:
        try:
            async with self.bot.http_session.get(url) as resp:
                resp.raise_for_status()
                data = await resp.read()
        except Exception as exc:
            log.warning("Image non téléchargée (%s), lien direct utilisé", exc)
            return None
        return discord.File(io.BytesIO(data), filename=IMAGE_NAME)

    # --- Commandes ---

    @live.command(name="tiktok", description="Annoncer ton live TikTok dans le salon des notifications")
    async def live_tiktok(self, interaction: discord.Interaction) -> None:
        username = (self.bot.config.tiktok_username or "").lstrip("@")
        if not username:
            raise UserError("TIKTOK_USERNAME n'est pas renseigné dans la configuration du bot.")
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.announce(
            Announcement(
                platform="tiktok_live",
                content_id=str(interaction.id),
                headline=f"**{username}** est en live sur TikTok ! 🔴",
                title="Live TikTok en cours",
                url=f"https://www.tiktok.com/@{username}/live",
                footer="TikTok",
                button_label="Rejoindre le live",
                author_name=f"@{username}",
                description="Rejoins le live maintenant !",
                timestamp=discord.utils.utcnow(),
            )
        )
        await interaction.followup.send("✅ Live TikTok annoncé.", ephemeral=True)


async def setup(bot: BimouIA) -> None:
    await bot.add_cog(Notifications(bot))
