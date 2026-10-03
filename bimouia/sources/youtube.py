"""Vidéos YouTube : lecture du flux RSS public de la chaîne (aucune clé nécessaire)."""

import xml.etree.ElementTree as ET
from datetime import datetime

import aiohttp

from ..announcements import Announcement

FEED_URL = "https://www.youtube.com/feeds/videos.xml"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


def parse_feed(xml_text: str) -> list[Announcement]:
    """Transforme le flux en annonces, du plus ancien au plus récent."""
    root = ET.fromstring(xml_text)
    channel = root.findtext("atom:author/atom:name", namespaces=NS) or root.findtext("atom:title", namespaces=NS)
    items: list[Announcement] = []
    for entry in root.findall("atom:entry", NS):
        video_id = entry.findtext("yt:videoId", namespaces=NS)
        if not video_id:
            continue
        link = entry.find("atom:link[@rel='alternate']", NS)
        thumbnail = entry.find("media:group/media:thumbnail", NS)
        published = entry.findtext("atom:published", namespaces=NS)
        items.append(
            Announcement(
                platform="youtube",
                content_id=video_id,
                headline=f"Nouvelle vidéo YouTube de **{channel}** ! 🎬",
                title=entry.findtext("atom:title", default="Nouvelle vidéo", namespaces=NS),
                url=link.get("href") if link is not None else f"https://www.youtube.com/watch?v={video_id}",
                footer="YouTube",
                button_label="Regarder la vidéo",
                author_name=channel,
                image_url=thumbnail.get("url") if thumbnail is not None else None,
                timestamp=datetime.fromisoformat(published) if published else None,
            )
        )
    items.reverse()
    return items


class YouTubeSource:
    platform = "youtube"
    seed_on_first_run = True

    def __init__(self, session: aiohttp.ClientSession, channel_id: str, interval: int) -> None:
        self._session = session
        self._channel_id = channel_id
        self.interval = interval

    async def fetch(self) -> list[Announcement]:
        async with self._session.get(FEED_URL, params={"channel_id": self._channel_id}) as resp:
            resp.raise_for_status()
            return parse_feed(await resp.text())
