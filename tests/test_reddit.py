from src.sources import reddit

SAMPLE = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title>top scoring links : pettyrevenge</title>
<entry>
<author><name>/u/alice</name></author>
<category term="pettyrevenge" label="r/pettyrevenge"/>
<content type="html">&lt;!-- SC_OFF --&gt;&lt;div class=&quot;md&quot;&gt;&lt;p&gt;My neighbor kept parking in my spot so I had his car towed.&lt;/p&gt;&lt;/div&gt;&lt;!-- SC_ON --&gt; &amp;#32; submitted by &amp;#32; &lt;a href=&quot;https://www.reddit.com/user/alice&quot;&gt; /u/alice &lt;/a&gt; &lt;br/&gt; &lt;span&gt;&lt;a href=&quot;x&quot;&gt;[link]&lt;/a&gt;&lt;/span&gt;</content>
<id>t3_abc123</id>
<link href="https://www.reddit.com/r/pettyrevenge/comments/abc123/spot/" />
<published>2026-07-04T04:27:43+00:00</published>
<title>Parking spot revenge</title>
</entry>
</feed>'''

def make_get(text, status=200):
    def _get(url, headers=None, timeout=None):
        class R:
            status_code = status
            def __init__(self): self.text = text
        return R()
    return _get

def test_fetch_parses_rss_entry_into_rawpost():
    posts = reddit.fetch(["pettyrevenge"], http_get=make_get(SAMPLE))
    assert len(posts) == 1
    p = posts[0]
    assert p.id == "abc123"                       # t3_ stripped
    assert p.title == "Parking spot revenge"
    assert p.subreddit == "pettyrevenge"
    assert p.url.endswith("/abc123/spot/")
    assert "parking in my spot" in p.body.lower()
    assert "submitted by" not in p.body.lower()   # footer stripped
    assert "<" not in p.body                        # html tags stripped
    assert p.created_utc > 0

def test_fetch_uses_rss_endpoint_and_browser_ua():
    seen = {}
    def _get(url, headers=None, timeout=None):
        seen["url"] = url; seen["ua"] = headers.get("User-Agent", "")
        class R:
            status_code = 200
            text = SAMPLE
        return R()
    reddit.fetch(["pettyrevenge"], http_get=_get)
    assert seen["url"] == "https://www.reddit.com/r/pettyrevenge/top/.rss?t=day&limit=25"
    assert "Mozilla" in seen["ua"]

def test_fetch_skips_non_200():
    posts = reddit.fetch(["pettyrevenge"], http_get=make_get("", status=403))
    assert posts == []

def test_fetch_sleeps_between_subreddits_to_avoid_rate_limit():
    n = {"sleeps": 0}
    def _get(url, headers=None, timeout=None):
        class R:
            status_code = 200
            text = SAMPLE
        return R()
    reddit.fetch(["a", "b", "c"], http_get=_get, sleep=lambda s: n.__setitem__("sleeps", n["sleeps"] + 1))
    assert n["sleeps"] == 2   # gaps BETWEEN 3 requests, none before the first

def test_fetch_early_exits_once_enough_gathered():
    calls = {"n": 0}
    def _get(url, headers=None, timeout=None):
        calls["n"] += 1
        class R:
            status_code = 200
            text = SAMPLE
        return R()
    posts = reddit.fetch(["a", "b", "c", "d"], http_get=_get, sleep=lambda s: None, enough=2)
    assert calls["n"] == 2          # stopped after 2 subs (SAMPLE yields 1 post each)
    assert len(posts) == 2

def test_fetch_retries_once_on_429_then_succeeds():
    seq = [429, 200]
    slept = []
    def _get(url, headers=None, timeout=None):
        code = seq.pop(0)
        class R:
            status_code = code
            text = SAMPLE
        return R()
    posts = reddit.fetch(["a"], http_get=_get, sleep=lambda s: slept.append(s))
    assert len(posts) == 1          # succeeded on the retry
    assert 20 in slept              # backed off 20s before retrying
