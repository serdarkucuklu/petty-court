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

def test_feed_has_apple_required_itunes_tags():
    show = {"title": "Petty Court", "author": "Petty Court", "description": "d",
            "language": "en-us", "base_url": "https://x.github.io/pc", "cover": "assets/cover.png",
            "email": "owner@example.com", "category": "Comedy", "explicit": "no"}
    eps = [{"id": "a", "title": "Ep 1", "audio": "ep1.mp3", "description": "n",
            "length_bytes": 1000, "pub_date": "2026-07-04T10:00:00+00:00"}]
    xml = rss.build_feed(show, eps, show["base_url"])
    # Apple rejects a feed missing any of these
    assert 'itunes:image href="https://x.github.io/pc/cover.png"' in xml
    assert 'itunes:category text="Comedy"' in xml
    assert "<itunes:explicit>no</itunes:explicit>" in xml
    assert "<itunes:email>owner@example.com</itunes:email>" in xml
    assert "<itunes:owner>" in xml
