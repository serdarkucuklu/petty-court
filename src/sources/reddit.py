import requests
from src.models import RawPost

UA = "petty-court-bot/1.0 (podcast automation)"

def fetch(subreddits, limit=25, http_get=requests.get):
    posts = []
    for sub in subreddits:
        url = f"https://www.reddit.com/r/{sub}/top.json?t=day&limit={limit}"
        resp = http_get(url, headers={"User-Agent": UA}, timeout=20)
        if getattr(resp, "status_code", 200) != 200:
            continue
        for child in resp.json().get("data", {}).get("children", []):
            d = child["data"]
            if d.get("over_18") or d.get("stickied") or not d.get("selftext"):
                continue
            posts.append(RawPost(
                id=d["id"], subreddit=d["subreddit"], title=d["title"],
                body=d["selftext"], score=d["score"],
                url="https://www.reddit.com" + d["permalink"], created_utc=d["created_utc"],
            ))
    return posts
