"""Annonce d'un contenu (live ou publication) et sa mise en forme Discord."""

from dataclasses import dataclass, field
from datetime import datetime

import discord

from .ui import ACCENT


@dataclass
class Announcement:
    platform: str  # clé de déduplication : "twitch", "youtube", "tiktok"
    content_id: str
    headline: str  # phrase fixe affichée à côté de la mention @notifs
    title: str
    url: str
    footer: str
    button_label: str
    author_name: str | None = None
    author_icon: str | None = None
    description: str | None = None
    image_url: str | None = None
    attach_image: bool = False  # recopie l'image dans Discord (liens d'image qui expirent)
    timestamp: datetime | None = None
    fields: list[tuple[str, str]] = field(default_factory=list)


def build_embed(item: Announcement, image_url: str | None = None) -> discord.Embed:
    embed = discord.Embed(
        title=item.title[:256],
        url=item.url,
        description=item.description,
        colour=ACCENT,
        timestamp=item.timestamp,
    )
    if item.author_name:
        embed.set_author(name=item.author_name[:256], url=item.url, icon_url=item.author_icon)
    for name, value in item.fields:
        embed.add_field(name=name, value=value, inline=True)
    if image_url or item.image_url:
        embed.set_image(url=image_url or item.image_url)
    embed.set_footer(text=item.footer)
    return embed


def build_view(item: Announcement) -> discord.ui.View:
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label=item.button_label, url=item.url, style=discord.ButtonStyle.link))
    return view
