"""Messages à réactions : chaque emoji donne un rôle, retirer sa réaction retire le rôle."""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

from ..ui import ACCENT, UserError, chunk_lines, reply_error

if TYPE_CHECKING:
    from ..bot import BimouIA

log = logging.getLogger(__name__)

MAX_ROLES = 20  # limite Discord de réactions différentes par message
REASON = "Rôle-réaction BimouIA"
MESSAGE_ID_RE = re.compile(r"(\d{15,25})/?$")
MODE_CHOICES = [
    Choice(name="Plusieurs rôles possibles", value="multiple"),
    Choice(name="Un seul rôle à la fois", value="unique"),
]
# Rôles jamais distribués en libre-service : ils donnent des pouvoirs de modération
DANGEROUS = discord.Permissions(
    administrator=True, manage_guild=True, manage_roles=True, manage_channels=True,
    manage_webhooks=True, manage_messages=True, kick_members=True, ban_members=True,
    moderate_members=True, mention_everyone=True,
)


def emoji_key(emoji: discord.PartialEmoji) -> str:
    """Identifiant stable d'un emoji : l'id pour un emoji du serveur, le caractère sinon."""
    if emoji.id:
        return str(emoji.id)
    # Le sélecteur de variante (U+FE0F) varie selon l'appareil : on l'ignore
    return (emoji.name or "").replace("️", "")


def parse_message_id(value: str | None) -> int | None:
    """Accepte un identifiant de message ou un lien de message Discord."""
    match = MESSAGE_ID_RE.search((value or "").strip())
    return int(match.group(1)) if match else None


@dataclass
class RoleEntry:
    emoji_key: str
    emoji_display: str
    role_id: int


@dataclass
class ReactionMessage:
    message_id: int
    guild_id: int
    channel_id: int
    title: str
    body: str
    single_choice: bool
    roles: dict[str, RoleEntry] = field(default_factory=dict)  # dans l'ordre d'ajout


def build_embed(msg: ReactionMessage) -> discord.Embed:
    embed = discord.Embed(title=msg.title, description=msg.body, colour=ACCENT)
    lines = [f"{entry.emoji_display}  ·  <@&{entry.role_id}>" for entry in msg.roles.values()]
    for index, chunk in enumerate(chunk_lines(lines, 1024)):
        embed.add_field(name="Rôles disponibles" if index == 0 else "​", value=chunk, inline=False)
    mode = "Un seul rôle à la fois" if msg.single_choice else "Plusieurs rôles possibles"
    embed.set_footer(text=f"{mode} · Réagis pour obtenir un rôle, retire ta réaction pour le perdre")
    return embed


class MessageModal(discord.ui.Modal):
    """Fenêtre de saisie du titre et du texte d'un message à réactions."""

    def __init__(self, on_done: Callable[[discord.Interaction, str, str], Awaitable[None]],
                 title_default: str = "", body_default: str = "") -> None:
        super().__init__(title="Message à réactions", timeout=900)
        self._on_done = on_done
        self.title_input = discord.ui.TextInput(label="Titre", max_length=256,
                                                default=title_default or None)
        self.body_input = discord.ui.TextInput(label="Texte", style=discord.TextStyle.paragraph,
                                               max_length=3500, default=body_default or None)
        self.add_item(self.title_input)
        self.add_item(self.body_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self._on_done(interaction, self.title_input.value.strip(), self.body_input.value.strip())

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await reply_error(interaction, error)


class ReactionRoles(commands.Cog):
    group = app_commands.Group(
        name="reactions",
        description="Messages à réactions qui donnent des rôles",
        guild_only=True,
        default_permissions=discord.Permissions(manage_roles=True),
    )

    def __init__(self, bot: BimouIA) -> None:
        self.bot = bot
        self.messages: dict[int, ReactionMessage] = {}

    async def cog_load(self) -> None:
        # Cache mémoire : aucune requête en base à chaque réaction
        for row in await self.bot.db.fetchall("SELECT * FROM reaction_messages ORDER BY created_at"):
            self.messages[row["message_id"]] = ReactionMessage(
                row["message_id"], row["guild_id"], row["channel_id"],
                row["title"], row["body"], bool(row["single_choice"]),
            )
        rows = await self.bot.db.fetchall(
            "SELECT message_id, emoji_key, emoji_display, role_id FROM reaction_roles ORDER BY id")
        for row in rows:
            if msg := self.messages.get(row["message_id"]):
                msg.roles[row["emoji_key"]] = RoleEntry(row["emoji_key"], row["emoji_display"], row["role_id"])
        log.info("%d message(s) à réactions chargé(s)", len(self.messages))

    # --- Outils internes ---

    def _get(self, value: str, guild_id: int | None) -> ReactionMessage:
        msg = self.messages.get(parse_message_id(value) or 0)
        if msg is None or msg.guild_id != guild_id:
            raise UserError("Message introuvable. Choisis-le dans la liste proposée.")
        return msg

    async def _fetch(self, msg: ReactionMessage) -> discord.Message:
        try:
            channel = self.bot.get_channel(msg.channel_id) or await self.bot.fetch_channel(msg.channel_id)
            return await channel.fetch_message(msg.message_id)
        except discord.NotFound:
            await self._forget(msg.message_id)
            raise UserError("Ce message a été supprimé de Discord : il est retiré de la liste.") from None
        except discord.Forbidden:
            raise UserError("BimouIA n'a plus accès au salon de ce message.") from None

    async def _forget(self, message_id: int) -> None:
        self.messages.pop(message_id, None)
        await self.bot.db.execute("DELETE FROM reaction_messages WHERE message_id = %s", (message_id,))

    def _check_role(self, interaction: discord.Interaction, role: discord.Role) -> None:
        me = interaction.guild.me
        author = interaction.user
        if role.is_default() or role.managed:
            raise UserError(f"{role.mention} est géré par Discord ou une intégration (Twitch…) : "
                            "le bot ne peut pas le donner.")
        if not me.guild_permissions.manage_roles:
            raise UserError("BimouIA n'a pas la permission « Gérer les rôles ».")
        if role >= me.top_role:
            raise UserError(f"Place le rôle **{me.top_role.name}** au-dessus de {role.mention} "
                            "(Paramètres du serveur → Rôles).")
        if author.id != interaction.guild.owner_id and role >= author.top_role:
            raise UserError(f"{role.mention} est égal ou supérieur à ton rôle le plus haut.")
        if role.permissions.value & DANGEROUS.value:
            raise UserError(f"{role.mention} donne des pouvoirs de modération : "
                            "il ne peut pas être distribué par réaction.")

    # --- Commandes ---

    @group.command(name="creer", description="Écrire et publier un nouveau message à réactions")
    @app_commands.describe(salon="Salon de publication (par défaut : ce salon)",
                           mode="Les membres peuvent-ils cumuler les rôles de ce message ?")
    @app_commands.choices(mode=MODE_CHOICES)
    async def create(self, interaction: discord.Interaction, salon: discord.TextChannel | None = None,
                     mode: Choice[str] | None = None) -> None:
        channel = salon or interaction.channel
        if not isinstance(channel, discord.TextChannel):
            raise UserError("Choisis un salon textuel.")
        perms = channel.permissions_for(interaction.guild.me)
        required = {
            "Voir le salon": perms.view_channel,
            "Envoyer des messages": perms.send_messages,
            "Intégrer des liens": perms.embed_links,
            "Ajouter des réactions": perms.add_reactions,
            "Voir les anciens messages": perms.read_message_history,
        }
        if missing := [name for name, ok in required.items() if not ok]:
            raise UserError(f"Dans {channel.mention}, BimouIA n'a pas : {', '.join(missing)}.")
        single = mode is not None and mode.value == "unique"

        async def publish(modal_interaction: discord.Interaction, title: str, body: str) -> None:
            msg = ReactionMessage(0, channel.guild.id, channel.id, title, body, single)
            sent = await channel.send(embed=build_embed(msg))
            msg.message_id = sent.id
            await self.bot.db.execute(
                "INSERT INTO reaction_messages (message_id, guild_id, channel_id, title, body, single_choice) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (msg.message_id, msg.guild_id, msg.channel_id, title, body, single),
            )
            self.messages[msg.message_id] = msg
            await modal_interaction.response.send_message(
                f"✅ Message publié : {sent.jump_url}\nAjoute les rôles avec `/reactions ajouter`.",
                ephemeral=True,
            )

        await interaction.response.send_modal(MessageModal(publish))

    @group.command(name="ajouter", description="Associer un emoji à un rôle sur un message à réactions")
    @app_commands.describe(message="Message à réactions", emoji="Emoji sur lequel cliquer",
                           role="Rôle donné aux membres")
    async def add(self, interaction: discord.Interaction, message: str, emoji: str,
                  role: discord.Role) -> None:
        msg = self._get(message, interaction.guild_id)
        self._check_role(interaction, role)
        if len(msg.roles) >= MAX_ROLES:
            raise UserError(f"Un message accepte au maximum {MAX_ROLES} emojis.")
        partial = discord.PartialEmoji.from_str(emoji.strip())
        key = emoji_key(partial)
        if not key:
            raise UserError("Emoji invalide.")
        if key in msg.roles:
            raise UserError(f"{msg.roles[key].emoji_display} est déjà utilisé sur ce message. "
                            "Retire-le d'abord avec `/reactions retirer`.")

        await interaction.response.defer(ephemeral=True, thinking=True)
        discord_message = await self._fetch(msg)
        try:
            await discord_message.add_reaction(partial)
        except discord.HTTPException:
            raise UserError("Emoji invalide ou inaccessible : utilise un emoji standard "
                            "ou un emoji de ce serveur.") from None
        entry = RoleEntry(key, str(partial), role.id)
        await self.bot.db.execute(
            "INSERT INTO reaction_roles (message_id, emoji_key, emoji_display, role_id) VALUES (%s, %s, %s, %s)",
            (msg.message_id, entry.emoji_key, entry.emoji_display, entry.role_id),
        )
        msg.roles[key] = entry
        await discord_message.edit(embed=build_embed(msg))
        await interaction.followup.send(f"✅ {entry.emoji_display} → {role.mention} ajouté.", ephemeral=True)

    @group.command(name="retirer", description="Retirer un emoji (et son rôle) d'un message à réactions")
    @app_commands.describe(message="Message à réactions", emoji="Emoji à retirer")
    async def remove(self, interaction: discord.Interaction, message: str, emoji: str) -> None:
        msg = self._get(message, interaction.guild_id)
        entry = msg.roles.get(emoji_key(discord.PartialEmoji.from_str(emoji.strip())))
        if entry is None:
            raise UserError("Cet emoji n'est pas utilisé sur ce message.")

        await interaction.response.defer(ephemeral=True, thinking=True)
        discord_message = await self._fetch(msg)
        await self.bot.db.execute(
            "DELETE FROM reaction_roles WHERE message_id = %s AND emoji_key = %s",
            (msg.message_id, entry.emoji_key),
        )
        del msg.roles[entry.emoji_key]
        partial = discord.PartialEmoji.from_str(entry.emoji_display)
        try:
            await discord_message.clear_reaction(partial)
        except discord.Forbidden:
            # Sans « Gérer les messages », on retire au moins la réaction du bot
            await discord_message.remove_reaction(partial, self.bot.user)
        await discord_message.edit(embed=build_embed(msg))
        await interaction.followup.send(
            f"✅ {entry.emoji_display} retiré. Les membres qui avaient <@&{entry.role_id}> le gardent.",
            ephemeral=True,
        )

    @group.command(name="modifier", description="Modifier le texte ou le mode d'un message à réactions")
    @app_commands.describe(message="Message à réactions", mode="Nouveau mode (inchangé si vide)")
    @app_commands.choices(mode=MODE_CHOICES)
    async def edit(self, interaction: discord.Interaction, message: str,
                   mode: Choice[str] | None = None) -> None:
        msg = self._get(message, interaction.guild_id)

        async def save(modal_interaction: discord.Interaction, title: str, body: str) -> None:
            await modal_interaction.response.defer(ephemeral=True, thinking=True)
            discord_message = await self._fetch(msg)
            single = msg.single_choice if mode is None else mode.value == "unique"
            await self.bot.db.execute(
                "UPDATE reaction_messages SET title = %s, body = %s, single_choice = %s WHERE message_id = %s",
                (title, body, single, msg.message_id),
            )
            msg.title, msg.body, msg.single_choice = title, body, single
            await discord_message.edit(embed=build_embed(msg))
            await modal_interaction.followup.send(f"✅ Message modifié : {discord_message.jump_url}",
                                                  ephemeral=True)

        await interaction.response.send_modal(MessageModal(save, msg.title, msg.body))

    # --- Autocomplétion : choisir un message ou un emoji dans une liste ---

    @edit.autocomplete("message")
    @remove.autocomplete("message")
    @add.autocomplete("message")
    async def message_autocomplete(self, interaction: discord.Interaction, current: str) -> list[Choice[str]]:
        current = current.lower()
        choices: list[Choice[str]] = []
        for msg in reversed(self.messages.values()):  # les plus récents d'abord
            if msg.guild_id != interaction.guild_id or current not in msg.title.lower():
                continue
            channel = self.bot.get_channel(msg.channel_id)
            label = f"{msg.title} (#{channel.name})" if channel else msg.title
            choices.append(Choice(name=label[:100], value=str(msg.message_id)))
            if len(choices) == 25:
                break
        return choices

    @remove.autocomplete("emoji")
    async def emoji_autocomplete(self, interaction: discord.Interaction, current: str) -> list[Choice[str]]:
        msg = self.messages.get(parse_message_id(interaction.namespace.message) or 0)
        if msg is None or msg.guild_id != interaction.guild_id:
            return []
        choices: list[Choice[str]] = []
        for entry in msg.roles.values():
            emoji = discord.PartialEmoji.from_str(entry.emoji_display)
            role = interaction.guild.get_role(entry.role_id)
            label = f"{f':{emoji.name}:' if emoji.id else emoji.name} → {role.name if role else 'rôle supprimé'}"
            if current.lower() in label.lower():
                choices.append(Choice(name=label[:100], value=entry.emoji_key))
        return choices[:25]

    # --- Événements Discord ---

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        msg = self.messages.get(payload.message_id)
        member = payload.member
        if msg is None or member is None or member.bot:
            return
        entry = msg.roles.get(emoji_key(payload.emoji))
        if entry is None:
            return
        role = member.guild.get_role(entry.role_id)
        if role is None:
            log.warning("Rôle %s introuvable (message %s)", entry.role_id, msg.message_id)
            return
        try:
            if role not in member.roles:
                await member.add_roles(role, reason=REASON)
            if msg.single_choice:
                await self._remove_other_roles(msg, entry, member)
        except discord.Forbidden:
            log.warning("Permissions insuffisantes pour gérer le rôle %s", role.name)

    async def _remove_other_roles(self, msg: ReactionMessage, keep: RoleEntry, member: discord.Member) -> None:
        # Mode « un seul rôle » : on retire les autres rôles du message et leurs réactions
        others = [e for e in msg.roles.values() if e is not keep and member.get_role(e.role_id)]
        if not others:
            return
        await member.remove_roles(*(discord.Object(e.role_id) for e in others), reason=REASON)
        partial_message = self.bot.get_partial_messageable(msg.channel_id).get_partial_message(msg.message_id)
        for entry in others:
            try:
                await partial_message.remove_reaction(discord.PartialEmoji.from_str(entry.emoji_display), member)
            except discord.HTTPException:
                log.warning("Impossible de retirer la réaction %s (permission « Gérer les messages » ?)",
                            entry.emoji_display)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        msg = self.messages.get(payload.message_id)
        if msg is None or payload.guild_id is None or payload.user_id == self.bot.user.id:
            return
        entry = msg.roles.get(emoji_key(payload.emoji))
        guild = self.bot.get_guild(payload.guild_id)
        if entry is None or guild is None:
            return
        member = guild.get_member(payload.user_id)
        if member is None:
            try:
                member = await guild.fetch_member(payload.user_id)
            except discord.NotFound:
                return
        if member.bot or not member.get_role(entry.role_id):
            return
        try:
            await member.remove_roles(discord.Object(entry.role_id), reason=REASON)
        except discord.Forbidden:
            log.warning("Permissions insuffisantes pour retirer le rôle %s", entry.role_id)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent) -> None:
        if payload.message_id in self.messages:
            await self._forget(payload.message_id)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent) -> None:
        for message_id in payload.message_ids & self.messages.keys():
            await self._forget(message_id)


async def setup(bot: BimouIA) -> None:
    await bot.add_cog(ReactionRoles(bot))
