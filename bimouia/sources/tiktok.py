"""Vidéos TikTok : API officielle (Login Kit + Display API), jetons OAuth stockés en base."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import aiohttp

from ..announcements import Announcement
from ..db import Database
from . import SourceNotReady

log = logging.getLogger(__name__)

AUTHORIZE_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
VIDEO_LIST_URL = "https://open.tiktokapis.com/v2/video/list/"
USER_INFO_URL = "https://open.tiktokapis.com/v2/user/info/"
SCOPES = "user.info.basic,video.list"
VIDEO_FIELDS = "id,title,video_description,cover_image_url,share_url,create_time"
PROVIDER = "tiktok"
RECONNECT_HINT = "Connecte ton compte TikTok : docker compose run --rm bot python -m bimouia.tiktok_auth"


def _utcnow() -> datetime:
    # Heure UTC sans fuseau, au même format que la colonne DATETIME
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TikTokAuth:
    """Gestion des jetons OAuth TikTok (connexion initiale et renouvellement)."""

    def __init__(self, session: aiohttp.ClientSession, db: Database, client_key: str,
                 client_secret: str, redirect_uri: str) -> None:
        self._session = session
        self._db = db
        self._client_key = client_key
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri

    def authorize_url(self, state: str) -> str:
        params = {
            "client_key": self._client_key,
            "scope": SCOPES,
            "response_type": "code",
            "redirect_uri": self._redirect_uri,
            "state": state,
        }
        return f"{AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> None:
        await self._request_token({"grant_type": "authorization_code", "code": code,
                                   "redirect_uri": self._redirect_uri})

    async def access_token(self, force_refresh: bool = False) -> str:
        row = await self._db.fetchone(
            "SELECT access_token, refresh_token, expires_at FROM oauth_tokens WHERE provider = %s",
            (PROVIDER,),
        )
        if row is None:
            raise SourceNotReady(RECONNECT_HINT)
        if not force_refresh and row["expires_at"] - timedelta(minutes=5) > _utcnow():
            return row["access_token"]
        try:
            return await self._request_token({"grant_type": "refresh_token",
                                              "refresh_token": row["refresh_token"]})
        except RuntimeError as exc:
            # Jeton de renouvellement expiré ou révoqué : il faut se reconnecter
            raise SourceNotReady(f"{exc}. {RECONNECT_HINT}") from exc

    async def _request_token(self, data: dict[str, str]) -> str:
        form = {"client_key": self._client_key, "client_secret": self._client_secret, **data}
        async with self._session.post(TOKEN_URL, data=form) as resp:
            body = await resp.json(content_type=None)
        if "access_token" not in body:
            raise RuntimeError(f"TikTok refuse le jeton : {body.get('error_description') or body}")
        await self._db.execute(
            "REPLACE INTO oauth_tokens (provider, access_token, refresh_token, expires_at) "
            "VALUES (%s, %s, %s, %s)",
            (PROVIDER, body["access_token"], body["refresh_token"],
             _utcnow() + timedelta(seconds=int(body["expires_in"]))),
        )
        return body["access_token"]


def video_to_announcement(video: dict[str, Any], display_name: str, avatar: str | None) -> Announcement:
    caption = (video.get("video_description") or "").strip()
    title = (video.get("title") or "").strip() or caption.split("\n", 1)[0].strip() or "Nouvelle vidéo"
    created = video.get("create_time")
    return Announcement(
        platform="tiktok",
        content_id=str(video["id"]),
        headline=f"Nouvelle vidéo TikTok de **{display_name}** ! 🎬",
        title=title,
        url=video.get("share_url") or "https://www.tiktok.com",
        footer="TikTok",
        button_label="Regarder la vidéo",
        author_name=display_name,
        author_icon=avatar,
        image_url=video.get("cover_image_url"),
        attach_image=True,  # les liens d'image TikTok expirent
        timestamp=datetime.fromtimestamp(created, tz=timezone.utc) if created else None,
    )


class TikTokVideoSource:
    platform = "tiktok"
    seed_on_first_run = True

    def __init__(self, session: aiohttp.ClientSession, auth: TikTokAuth, interval: int) -> None:
        self._session = session
        self._auth = auth
        self.interval = interval
        self._user: dict[str, Any] | None = None

    async def _api(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        for attempt in range(2):
            token = await self._auth.access_token(force_refresh=attempt == 1)
            headers = {"Authorization": f"Bearer {token}"}
            async with self._session.request(method, url, headers=headers, **kwargs) as resp:
                body = await resp.json(content_type=None)
            error = body.get("error", {})
            if error.get("code") == "ok":
                return body.get("data", {})
            if error.get("code") != "access_token_invalid":
                break
        raise RuntimeError(f"Erreur API TikTok : {error.get('code')} – {error.get('message')}")

    async def fetch(self) -> list[Announcement]:
        if self._user is None:
            data = await self._api("GET", USER_INFO_URL, params={"fields": "display_name,avatar_url"})
            self._user = data.get("user", {})
        data = await self._api("POST", VIDEO_LIST_URL, params={"fields": VIDEO_FIELDS},
                               json={"max_count": 20})
        name = self._user.get("display_name") or "TikTok"
        avatar = self._user.get("avatar_url")
        # L'API renvoie les vidéos de la plus récente à la plus ancienne
        return [video_to_announcement(v, name, avatar) for v in reversed(data.get("videos", []))]
