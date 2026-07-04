import json
from src import main, config, models
from src.state import State

def test_run_pipeline_happy_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "cover.png").write_bytes(b"x")
    cfg = config.Config(subreddits=["tifu"], min_score=100, min_len=5, max_len=9999,
        hosts={"Max": "Charon", "Ivy": "Kore"},
        show={"title": "PC", "author": "PC", "description": "d", "language": "en-us",
              "base_url": "https://x.github.io/pc", "cover": "assets/cover.png"},
        gemini_api_key="k")
    st = State(str(tmp_path / "state" / "history.json"))
    post = models.RawPost(id="a", subreddit="tifu", title="T", body="x"*50,
        score=5000, url="u", created_utc=1.0)
    deps = dict(
        fetch=lambda subs: [post],
        select_fn=lambda c: ("a", "funny"),
        script_fn=lambda prompt: json.dumps({"title": "Ep", "description": "d",
            "tags": ["t"], "lines": [{"speaker": "Max", "text": "hi"}]}),
        tts_fn=lambda text: b"\x00\x01"*12000,
        runner=lambda cmd, check: 0,          # no real ffmpeg
        yt_service=None,                       # skip youtube
    )
    result = main.run(cfg, st, deps)
    assert result["episode_id"] == "a"
    assert st.is_seen("a")
    assert st.episodes()[0]["description"] == "d"
    assert st.episodes()[0]["length_bytes"] == 0   # fake runner writes no real mp3
    import os as _os
    assert _os.path.isdir("output")               # run() created it
    assert _os.path.exists("output/feed.xml")      # RSS published
    assert _os.path.exists("output/cover.png")     # cover copied for Pages

def test_yt_service_none_when_env_partial(monkeypatch):
    from src import main
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "tok")
    monkeypatch.delenv("YOUTUBE_CLIENT_ID", raising=False)
    monkeypatch.delenv("YOUTUBE_CLIENT_SECRET", raising=False)
    assert main._yt_service_from_env() is None
