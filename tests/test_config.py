from src import config, models

def test_load_config(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "subreddits: [tifu]\nmin_score: 100\nmin_len: 10\nmax_len: 20\n"
        "hosts: {Max: Charon, Ivy: Kore}\n"
        "show: {title: T, author: A, description: D, base_url: U, cover: c.png, language: en-us}\n"
    )
    cfg = config.load(str(cfg_file))
    assert cfg.subreddits == ["tifu"]
    assert cfg.gemini_api_key == "test-key"
    assert cfg.hosts == {"Max": "Charon", "Ivy": "Kore"}

def test_models_construct():
    p = models.RawPost(id="a", subreddit="tifu", title="t", body="b", score=10, url="u", created_utc=1.0)
    s = models.DialogueScript(title="T", description="D", tags=["x"],
                              lines=[models.DialogueLine(speaker="Max", text="hi")])
    assert s.lines[0].speaker == "Max"
