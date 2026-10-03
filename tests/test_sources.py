from bimouia.sources.tiktok import video_to_announcement
from bimouia.sources.youtube import parse_feed

FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns:media="http://search.yahoo.com/mrss/" xmlns="http://www.w3.org/2005/Atom">
 <title>Bimou</title>
 <author><name>Bimou</name><uri>https://www.youtube.com/channel/UCxxx</uri></author>
 <entry>
  <yt:videoId>NEW</yt:videoId>
  <title>Vidéo récente</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=NEW"/>
  <published>2026-10-02T18:00:00+00:00</published>
  <media:group><media:thumbnail url="https://i.ytimg.com/vi/NEW/hqdefault.jpg" width="480" height="360"/></media:group>
 </entry>
 <entry>
  <yt:videoId>OLD</yt:videoId>
  <title>Vidéo ancienne</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=OLD"/>
  <published>2026-09-01T18:00:00+00:00</published>
 </entry>
</feed>"""


def test_parse_feed_du_plus_ancien_au_plus_recent():
    items = parse_feed(FEED)
    assert [i.content_id for i in items] == ["OLD", "NEW"]
    recent = items[1]
    assert recent.title == "Vidéo récente"
    assert recent.url == "https://www.youtube.com/watch?v=NEW"
    assert recent.image_url == "https://i.ytimg.com/vi/NEW/hqdefault.jpg"
    assert recent.author_name == "Bimou"
    assert recent.timestamp.year == 2026
    assert items[0].image_url is None


def test_tiktok_titre_de_secours():
    video = {"id": 7, "title": "", "video_description": "Première ligne\n#hashtag",
             "share_url": "https://www.tiktok.com/@bimou/video/7", "create_time": 1790000000}
    item = video_to_announcement(video, "Bimou", None)
    assert item.title == "Première ligne"
    assert item.content_id == "7"
    assert item.attach_image is True
    assert video_to_announcement({"id": 8}, "Bimou", None).title == "Nouvelle vidéo"
