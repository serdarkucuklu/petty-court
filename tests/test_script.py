import json
from src import script, models, config

def story():
    return models.SelectedStory(post=models.RawPost(id="a", subreddit="tifu", title="T",
        body="story body", score=9000, url="u", created_utc=1.0), reason="funny")

def cfg():
    return config.Config(subreddits=[], min_score=0, min_len=0, max_len=9999,
        hosts={"Max": "Charon", "Ivy": "Kore"},
        show={"title": "Petty Court"}, gemini_api_key="")

def test_build_prompt_mentions_hosts_and_story():
    p = script.build_prompt(story().post, cfg().hosts, cfg().show)
    assert "Max" in p and "Ivy" in p and "story body" in p

def test_generate_parses_json():
    fake = lambda prompt: json.dumps({"title": "Ep 1", "description": "d", "tags": ["drama"],
        "lines": [{"speaker": "Max", "text": "Welcome"}, {"speaker": "Ivy", "text": "Wild story"}]})
    s = script.generate(story(), cfg(), generate_fn=fake)
    assert isinstance(s, models.DialogueScript)
    assert s.title == "Ep 1"
    assert s.lines[1].speaker == "Ivy"
