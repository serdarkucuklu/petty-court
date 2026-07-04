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
