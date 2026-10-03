"""Lecture de la configuration depuis les variables d'environnement (fichier .env)."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Variable d'environnement manquante : {name}")
    return value


def _optional(name: str) -> str | None:
    return os.getenv(name, "").strip() or None


def _int(name: str, default: int | None = None) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        if default is None:
            raise RuntimeError(f"Variable d'environnement manquante : {name}")
        return default
    try:
        return int(value)
    except ValueError:
        raise RuntimeError(f"{name} doit être un nombre entier (reçu : {value!r})") from None


@dataclass(frozen=True)
class Config:
    # Discord
    discord_token: str
    guild_id: int
    notif_channel_id: int
    notif_role_id: int
    # MariaDB
    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_name: str
    # Twitch (live automatique)
    twitch_client_id: str | None
    twitch_client_secret: str | None
    twitch_login: str | None
    twitch_interval: int
    # YouTube (vidéos automatiques)
    youtube_channel_id: str | None
    youtube_interval: int
    # TikTok (live par commande, vidéos automatiques)
    tiktok_username: str | None
    tiktok_client_key: str | None
    tiktok_client_secret: str | None
    tiktok_redirect_uri: str | None
    tiktok_interval: int

    # Chaque source ne s'active que si sa configuration est complète
    @property
    def twitch_enabled(self) -> bool:
        return all((self.twitch_client_id, self.twitch_client_secret, self.twitch_login))

    @property
    def youtube_enabled(self) -> bool:
        return self.youtube_channel_id is not None

    @property
    def tiktok_videos_enabled(self) -> bool:
        return all((self.tiktok_client_key, self.tiktok_client_secret, self.tiktok_redirect_uri))


def load_config() -> Config:
    return Config(
        discord_token=_required("DISCORD_TOKEN"),
        guild_id=_int("DISCORD_GUILD_ID"),
        notif_channel_id=_int("NOTIF_CHANNEL_ID"),
        notif_role_id=_int("NOTIF_ROLE_ID"),
        db_host=_required("DB_HOST"),
        db_port=_int("DB_PORT", 3306),
        db_user=_required("DB_USER"),
        db_password=_required("DB_PASSWORD"),
        db_name=_required("DB_NAME"),
        twitch_client_id=_optional("TWITCH_CLIENT_ID"),
        twitch_client_secret=_optional("TWITCH_CLIENT_SECRET"),
        twitch_login=_optional("TWITCH_LOGIN"),
        twitch_interval=_int("TWITCH_INTERVAL", 60),
        youtube_channel_id=_optional("YOUTUBE_CHANNEL_ID"),
        youtube_interval=_int("YOUTUBE_INTERVAL", 300),
        tiktok_username=_optional("TIKTOK_USERNAME"),
        tiktok_client_key=_optional("TIKTOK_CLIENT_KEY"),
        tiktok_client_secret=_optional("TIKTOK_CLIENT_SECRET"),
        tiktok_redirect_uri=_optional("TIKTOK_REDIRECT_URI"),
        tiktok_interval=_int("TIKTOK_INTERVAL", 600),
    )
