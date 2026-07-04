from src import curate, models, config
from src.state import State

def mk(id, score, body): return models.RawPost(id=id, subreddit="tifu", title="t",
    body=body, score=score, url="u", created_utc=1.0)

def cfg():
    return config.Config(subreddits=["tifu"], min_score=1000, min_len=10, max_len=100,
                         hosts={}, show={}, gemini_api_key="")

def test_filter_applies_score_len_dedupe(tmp_path):
    st = State(str(tmp_path / "h.json")); st.record_episode("seen", "T", "a.mp3")
    posts = [mk("seen", 5000, "x"*50), mk("low", 10, "x"*50),
             mk("short", 5000, "x"*2), mk("ok", 5000, "x"*50)]
    out = curate.filter_candidates(posts, cfg(), st)
    assert [p.id for p in out] == ["ok"]

def test_pick_uses_select_fn():
    posts = [mk("a", 5000, "x"*50), mk("b", 5000, "x"*50)]
    sel = curate.pick(posts, select_fn=lambda c: ("b", "funnier"))
    assert sel.post.id == "b" and sel.reason == "funnier"

def test_pick_empty_returns_none():
    assert curate.pick([], select_fn=lambda c: ("", "")) is None
