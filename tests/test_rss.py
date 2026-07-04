from src.publish import rss

def test_build_feed_contains_items():
    show = {"title": "Petty Court", "author": "PC", "description": "d",
            "language": "en-us", "base_url": "https://x.github.io/pc", "cover": "cover.png"}
    eps = [{"id": "a", "title": "Ep 1", "audio": "ep1.mp3", "description": "n",
            "length_bytes": 1000, "pub_date": "2026-07-04T10:00:00+00:00"}]
    xml = rss.build_feed(show, eps, show["base_url"])
    assert "<rss" in xml
    assert "Ep 1" in xml
    assert "https://x.github.io/pc/ep1.mp3" in xml
