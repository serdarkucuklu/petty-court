import logging
import requests
from src.models import RawPost

log = logging.getLogger("pettycourt")

UA = "petty-court-bot/1.0 (podcast automation)"

def get_token(client_id, client_secret, http_post=requests.post):
    """Application-only OAuth (client_credentials) for a Reddit 'script' app.
    Returns a bearer access-token string."""
    resp = http_post(
        "https://www.reddit.com/api/v1/access_token",
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials"},
        headers={"User-Agent": UA}, timeout=20)
    resp.raise_for_status()
    return resp.json()["access_token"]

def fetch(subreddits, limit=25, http_get=requests.get, token=None):
    posts = []
    for sub in subreddits:
        if token:
            url = f"https://oauth.reddit.com/r/{sub}/top?t=day&limit={limit}"
            headers = {"User-Agent": UA, "Authorization": f"Bearer {token}"}
        else:
            url = f"https://www.reddit.com/r/{sub}/top.json?t=day&limit={limit}"
            headers = {"User-Agent": UA}
        resp = http_get(url, headers=headers, timeout=20)
        status = getattr(resp, "status_code", 200)
        if status != 200:
            log.warning("Reddit r/%s returned %s (auth/rate/block?) — skipping", sub, status)
            continue
        for child in resp.json().get("data", {}).get("children", []):
            d = child["data"]
            if d.get("over_18") or d.get("stickied") or not d.get("selftext"):
                continue
            posts.append(RawPost(
                id=d["id"], subreddit=d["subreddit"], title=d["title"],
                body=d["selftext"], score=d["score"],
                url="https://www.reddit.com" + d["permalink"], created_utc=d["created_utc"]))
    return posts
