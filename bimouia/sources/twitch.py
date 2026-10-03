"""Live Twitch : interrogation de l'API officielle Helix."""

import time
from datetime import datetime
from typing import Any

import aiohttp

from ..announcements import Announcement

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
API_URL = "https://api.twitch.tv/helix"


class TwitchSource:
    platform = "twitch"
    seed_on_first_run = False  # un live déjà en cours au démarrage est annoncé

    def __init__(self, session: aiohttp.ClientSession, client_id: str, client_secret: str,
                 login: str, interval: int) -> None:
        self._session = session
        self._client_id = client_id
        self._client_secret = client_secret
        self._login = login.lower()
        self.interval = interval
        self._token: str | None = None
        self._token_expires = 0.0
        self._user: dict[str, Any] | None = None

    async def _get_token(self) -> str:
        # Jeton d'application (sans compte utilisateur), renouvelé avant expiration
        if self._token and time.monotonic() < self._token_expires:
            return self._token
        params = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "grant_type": "client_credentials",
        }
        async with self._session.post(TOKEN_URL, params=params) as resp:
            resp.raise_for_status()
            data = await resp.json()
        self._token = data["access_token"]
        self._token_expires = time.monotonic() + data["expires_in"] - 300
        return self._token

    async def _get(self, path: str, params: dict[str, str]) -> list[dict[str, Any]]:
        for _ in range(2):
            headers = {"Client-Id": self._client_id, "Authorization": f"Bearer {await self._get_token()}"}
            async with self._session.get(f"{API_URL}/{path}", params=params, headers=headers) as resp:
                if resp.status == 401:
                    # Jeton révoqué : on en redemande un et on réessaie une fois
                    self._token = None
                    continue
                resp.raise_for_status()
                return (await resp.json())["data"]
        raise RuntimeError("Twitch refuse le jeton d'application (identifiants à vérifier)")

    async def fetch(self) -> list[Announcement]:
        streams = await self._get("streams", {"user_login": self._login})
        if not streams:
            return []
        stream = streams[0]
        if self._user is None:
            users = await self._get("users", {"login": self._login})
            self._user = users[0] if users else {}

        name = stream["user_name"]
        # Paramètre anti-cache : sinon Discord réaffiche une ancienne capture du live
        thumbnail = (
            stream["thumbnail_url"].replace("{width}", "1280").replace("{height}", "720")
            + f"?t={int(time.time())}"
        )
        fields = [("Catégorie", stream["game_name"])] if stream.get("game_name") else []
        return [
            Announcement(
                platform=self.platform,
                content_id=stream["id"],
                headline=f"**{name}** est en live sur Twitch ! 🔴",
                title=stream["title"] or f"Live de {name}",
                url=f"https://www.twitch.tv/{self._login}",
                footer="Twitch",
                button_label="Regarder le live",
                author_name=name,
                author_icon=self._user.get("profile_image_url"),
                image_url=thumbnail,
                timestamp=datetime.fromisoformat(stream["started_at"]),
                fields=fields,
            )
        ]
