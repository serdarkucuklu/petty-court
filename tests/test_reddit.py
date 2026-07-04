from src.sources import reddit

def fake_get(url, headers=None, timeout=None):
    class R:
        status_code = 200
        def json(self):
            return {"data": {"children": [
                {"data": {"id": "1", "subreddit": "tifu", "title": "T", "selftext": "long body",
                          "score": 5000, "permalink": "/r/tifu/1", "created_utc": 1.0,
                          "over_18": False, "stickied": False}}
            ]}}
    return R()

def test_fetch_maps_posts():
    posts = reddit.fetch(["tifu"], limit=1, http_get=fake_get)
    assert len(posts) == 1
    assert posts[0].id == "1"
    assert posts[0].url == "https://www.reddit.com/r/tifu/1"
    assert posts[0].score == 5000

def test_fetch_skips_nsfw_and_stickied():
    def g(url, headers=None, timeout=None):
        class R:
            status_code = 200
            def json(self):
                return {"data": {"children": [
                    {"data": {"id": "2", "subreddit": "tifu", "title": "T", "selftext": "b",
                              "score": 10, "permalink": "/x", "created_utc": 1.0,
                              "over_18": True, "stickied": False}},
                    {"data": {"id": "3", "subreddit": "tifu", "title": "T", "selftext": "b",
                              "score": 10, "permalink": "/x", "created_utc": 1.0,
                              "over_18": False, "stickied": True}},
                ]}}
        return R()
    assert reddit.fetch(["tifu"], http_get=g) == []

def test_get_token_returns_access_token():
    captured = {}
    def fake_post(url, auth=None, data=None, headers=None, timeout=None):
        captured.update(url=url, auth=auth, data=data)
        class R:
            def raise_for_status(self): pass
            def json(self): return {"access_token": "tok123", "token_type": "bearer"}
        return R()
    tok = reddit.get_token("cid", "csec", http_post=fake_post)
    assert tok == "tok123"
    assert captured["auth"] == ("cid", "csec")
    assert captured["data"] == {"grant_type": "client_credentials"}
    assert "access_token" in captured["url"]

def test_fetch_uses_oauth_endpoint_when_token_present():
    seen = {}
    def fake_get(url, headers=None, timeout=None):
        seen.update(url=url, headers=headers)
        class R:
            status_code = 200
            def json(self):
                return {"data": {"children": [
                    {"data": {"id": "9", "subreddit": "tifu", "title": "T", "selftext": "body",
                              "score": 5000, "permalink": "/r/tifu/9", "created_utc": 1.0,
                              "over_18": False, "stickied": False}}]}}
        return R()
    posts = reddit.fetch(["tifu"], http_get=fake_get, token="tok123")
    assert posts[0].id == "9"
    assert seen["url"].startswith("https://oauth.reddit.com/")
    assert seen["headers"]["Authorization"] == "Bearer tok123"

def test_fetch_uses_public_endpoint_when_no_token():
    seen = {}
    def fake_get(url, headers=None, timeout=None):
        seen["url"] = url
        class R:
            status_code = 200
            def json(self): return {"data": {"children": []}}
        return R()
    reddit.fetch(["tifu"], http_get=fake_get)   # no token
    assert seen["url"].startswith("https://www.reddit.com/") and seen["url"].endswith(".json?t=day&limit=25")
    assert "www.reddit.com" in seen["url"] and "oauth.reddit.com" not in seen["url"]
