"""Éléments visuels communs : couleurs de la charte byBim et erreurs affichées à l'utilisateur."""

import logging

import discord
from discord import app_commands

log = logging.getLogger(__name__)

# Rouge d'accent byBim : il ponctue (barre latérale des encadrés), jamais de grande surface
ACCENT = discord.Colour(0xE7000B)


class UserError(app_commands.AppCommandError):
    """Erreur prévue, dont le message s'affiche tel quel à l'auteur de la commande."""


async def reply_error(interaction: discord.Interaction, error: Exception) -> None:
    """Répond à l'auteur d'une commande ou d'une fenêtre en échec, en privé."""
    if isinstance(error, app_commands.CommandInvokeError):
        error = error.original
    if isinstance(error, UserError):
        message = str(error)
    elif isinstance(error, app_commands.CheckFailure):
        message = "Tu n'as pas la permission d'utiliser cette commande."
    else:
        log.error("Erreur pendant une commande", exc_info=error)
        message = "Une erreur inattendue est survenue. Elle est enregistrée dans les logs du bot."
    if interaction.response.is_done():
        await interaction.followup.send(f"❌ {message}", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ {message}", ephemeral=True)


def chunk_lines(lines: list[str], limit: int) -> list[str]:
    """Regroupe des lignes en blocs de `limit` caractères maximum (limite des champs Discord)."""
    chunks: list[str] = []
    current = ""
    for line in lines:
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit and current:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks
