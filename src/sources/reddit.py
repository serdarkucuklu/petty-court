import logging, re, html, calendar, time
import requests
from src.models import RawPost

# Browser UA: Reddit 403s generic/datacenter UAs on the JSON API but serves the public RSS feed.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")
log = logging.getLogger("pettycourt")

_TAG = re.compile(r"<[^>]+>")
_FOOTER = re.compile(r"submitted by.*", re.IGNORECASE | re.DOTALL)

def _clean_body(content_html):
    """Reddit RSS <content> is escaped HTML with a 'submitted by ... [link]' footer. Return plain body text."""
    text = html.unescape(content_html or "")
    text = _FOOTER.split(text)[0]     # drop the 'submitted by ...' footer
    text = _TAG.sub(" ", text)        # strip HTML tags
    text = html.unescape(text)        # unescape entities revealed after tag removal
    return re.sub(r"\s+", " ", text).strip()

def _entry_body(e):
    if e.get("content"):
        return e["content"][0].get("value", "")
    return e.get("summary", "")

def fetch(subreddits, limit=25, http_get=requests.get, delay=3.0, sleep=time.sleep):
    """Fetch top-of-day posts per subreddit from Reddit's keyless RSS feed.
    A polite `delay` between requests avoids Reddit's burst rate-limit (429 on rapid sequential hits)."""
    posts = []
    for i, sub in enumerate(subreddits):
        if i:
            sleep(delay)
        url = f"https://www.reddit.com/r/{sub}/top/.rss?t=day&limit={limit}"
        resp = http_get(url, headers={"User-Agent": UA}, timeout=20)
        status = getattr(resp, "status_code", 200)
        if status != 200:
            log.warning("Reddit r/%s RSS returned %s (block/rate?) — skipping", sub, status)
            continue
        posts.extend(_parse_feed(resp.text, sub))
    return posts

def _parse_feed(xml_text, sub):
    import feedparser
    out = []
    for e in feedparser.parse(xml_text).entries:
        pid = (e.get("id") or "").replace("t3_", "")
        body = _clean_body(_entry_body(e))
        if not pid or not body:
            continue
        created = 0.0
        if e.get("published_parsed"):
            created = float(calendar.timegm(e["published_parsed"]))
        out.append(RawPost(
            id=pid, subreddit=sub, title=e.get("title", ""),
            body=body, score=0, url=e.get("link", ""), created_utc=created))
    return out
