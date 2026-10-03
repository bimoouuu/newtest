import discord

from bimouia.cogs.reaction_roles import (
    ReactionMessage, RoleEntry, build_embed, emoji_key, parse_message_id,
)


def test_emoji_key_ignore_le_selecteur_de_variante():
    assert emoji_key(discord.PartialEmoji(name="❤️")) == emoji_key(discord.PartialEmoji(name="❤"))


def test_emoji_key_emoji_du_serveur():
    emoji = discord.PartialEmoji.from_str("<:bimou:123456789012345678>")
    assert emoji_key(emoji) == "123456789012345678"
    # Une valeur d'autocomplétion (la clé) redonne la même clé
    assert emoji_key(discord.PartialEmoji.from_str("123456789012345678")) == "123456789012345678"


def test_parse_message_id():
    assert parse_message_id("1234567890123456789") == 1234567890123456789
    lien = "https://discord.com/channels/111111111111111111/222222222222222222/333333333333333333"
    assert parse_message_id(lien) == 333333333333333333
    assert parse_message_id("n'importe quoi") is None
    assert parse_message_id(None) is None


def test_build_embed():
    msg = ReactionMessage(1, 2, 3, "Couleurs", "Choisis ta couleur", single_choice=True)
    msg.roles["🔴"] = RoleEntry("🔴", "🔴", 42)
    embed = build_embed(msg)
    assert embed.colour.value == 0xE7000B
    assert embed.fields[0].value == "🔴  ·  <@&42>"
    assert embed.footer.text.startswith("Un seul rôle")


def test_build_embed_decoupe_les_longues_listes():
    msg = ReactionMessage(1, 2, 3, "Titre", "Texte", single_choice=False)
    for i in range(20):
        key = str(10**17 + i)
        msg.roles[key] = RoleEntry(key, f"<a:emoji_au_nom_long_{i}:{key}>", 10**18 + i)
    embed = build_embed(msg)
    assert len(embed.fields) > 1
    assert all(len(f.value) <= 1024 for f in embed.fields)
    assert len(embed) <= 6000
