# Internet Drama Podcast Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Her gün otonom olarak Reddit'ten bir internet-drama hikayesi çekip, iki AI host'un konuştuğu bir podcast bölümüne dönüştüren, seslendiren ve RSS + YouTube'a yayınlayan bir Python pipeline kur.

**Architecture:** Tek yönlü pipeline — bağımsız, tek-sorumlu modüller (fetch → curate → script → voice → audio → video → publish → state). `main.py` orkestrasyon + aşama başına hata izolasyonu yapar. Dış servisler (Gemini, YouTube, Reddit) ince wrapper'lar arkasında; testlerde mock'lanır. Günlük GitHub Actions cron ile çalışır.

**Tech Stack:** Python 3.11+, `google-genai` (Gemini 2.5 Flash script + 2.5 multi-speaker TTS), `requests` (Reddit), `google-api-python-client`+`google-auth-oauthlib` (YouTube), `feedgen` (RSS), ffmpeg (sistem binary), pytest, PyYAML, GitHub Actions.

## Global Constraints

- **Dil:** Tüm yayınlanan içerik İngilizce (global pazar).
- **Sandbox izolasyonu:** Tüm kod `D:\AI\Playground\14-drama-podcast\` altında; `.venv` bu klasörde.
- **API key güvenliği:** Key'ler asla koda gömülmez — local'de `.env`, prod'da GHA Secrets. `.env` ve `.venv` gitignore.
- **Tek Gemini key:** Script + TTS aynı `GEMINI_API_KEY`.
- **Telif:** Reddit içeriği verbatim okunmaz — 2-host transformative reaksiyon. Açıklamada kaynak subreddit atfı.
- **Loudness:** Yayın MP3'ü ffmpeg `loudnorm` ile -16 LUFS.
- **TTS:** `MultiSpeakerVoiceConfig` tam 2 konuşmacı ister; ses adları config'ten.
- **Model ID'leri:** Script `gemini-2.5-flash`, TTS `gemini-2.5-flash-preview-tts`.
- **Hata izolasyonu:** Bir publish hedefi (YouTube) patlarsa diğeri (RSS) yayınlanmaya devam eder.
- **TDD + sık commit:** Her task kırmızı test → minimal implementasyon → yeşil → commit.

---

## File Structure

```
14-drama-podcast/
├─ .env.example
├─ .gitignore
├─ requirements.txt
├─ config.yaml
├─ src/
│  ├─ __init__.py
│  ├─ models.py            # dataclass'lar: RawPost, SelectedStory, DialogueLine, DialogueScript
│  ├─ config.py            # config.yaml + .env yükler
│  ├─ state.py            # history.json oku/yaz, dedupe, arşiv
│  ├─ sources/
│  │  ├─ __init__.py
│  │  └─ reddit.py        # subreddit havuzundan RawPost listesi
│  ├─ curate.py           # filtre + dedupe + Gemini seçimi → SelectedStory
│  ├─ script.py           # Gemini Flash: SelectedStory → DialogueScript
│  ├─ voice.py            # Gemini multi-speaker TTS: DialogueScript → WAV
│  ├─ audio.py            # ffmpeg: WAV → yayına hazır MP3
│  ├─ video.py            # ffmpeg: MP3 + kapak → MP4
│  ├─ publish/
│  │  ├─ __init__.py
│  │  ├─ rss.py           # feed.xml üret/güncelle
│  │  └─ youtube.py       # MP4 upload
│  └─ main.py             # orkestrasyon
├─ assets/                # intro.mp3, outro.mp3, cover.png (kullanıcı sağlar)
├─ output/                # üretilen bölümler (gitignore dışı: feed.xml + mp3 Pages'e)
├─ state/
│  └─ history.json
├─ tests/
│  ├─ __init__.py
│  ├─ test_config.py
│  ├─ test_state.py
│  ├─ test_reddit.py
│  ├─ test_curate.py
│  ├─ test_script.py
│  ├─ test_voice.py
│  ├─ test_audio.py
│  ├─ test_video.py
│  ├─ test_rss.py
│  └─ test_youtube.py
└─ .github/workflows/daily.yml
```

---

### Task 1: Scaffold + config + data models

**Files:**
- Create: `14-drama-podcast/.gitignore`, `.env.example`, `requirements.txt`, `config.yaml`
- Create: `src/__init__.py`, `src/models.py`, `src/config.py`
- Test: `tests/__init__.py`, `tests/test_config.py`

**Interfaces:**
- Produces: `models.RawPost(id, subreddit, title, body, score, url, created_utc)`, `models.SelectedStory(post: RawPost, reason: str)`, `models.DialogueLine(speaker: str, text: str)`, `models.DialogueScript(title, description, tags: list[str], lines: list[DialogueLine])`.
- Produces: `config.load(path="config.yaml") -> Config` with attrs `subreddits: list[str]`, `min_score: int`, `min_len: int`, `max_len: int`, `hosts: dict` (speaker→voice_name), `show: dict` (title, author, base_url, cover), `gemini_api_key: str`.

- [ ] **Step 1: Create project skeleton files**

`.gitignore`:
```
.venv/
.env
output/
__pycache__/
*.pyc
state/token.json
```

`.env.example`:
```
GEMINI_API_KEY=
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_REFRESH_TOKEN=
```

`requirements.txt`:
```
google-genai>=1.33.0
requests>=2.32
feedgen>=1.0
PyYAML>=6.0
google-api-python-client>=2.140
google-auth-oauthlib>=1.2
pytest>=8.0
```

`config.yaml`:
```yaml
subreddits: [AmItheAsshole, pettyrevenge, ProRevenge, MaliciousCompliance, entitledparents, tifu]
min_score: 2000
min_len: 800
max_len: 6000
hosts:
  Max: Charon      # S1 prebuilt voice
  Ivy: Kore        # S2 prebuilt voice
show:
  title: "Petty Court — Daily Internet Drama"
  author: "Petty Court"
  description: "Two hosts react to the internet's pettiest revenge and drama, every day."
  base_url: "https://<user>.github.io/petty-court"   # GitHub Pages URL
  cover: "assets/cover.png"
  language: "en-us"
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_config.py
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.config'`

- [ ] **Step 4: Implement models + config**

```python
# src/models.py
from dataclasses import dataclass, field

@dataclass
class RawPost:
    id: str; subreddit: str; title: str; body: str
    score: int; url: str; created_utc: float

@dataclass
class SelectedStory:
    post: RawPost
    reason: str

@dataclass
class DialogueLine:
    speaker: str
    text: str

@dataclass
class DialogueScript:
    title: str
    description: str
    tags: list
    lines: list = field(default_factory=list)
```

```python
# src/config.py
import os, yaml
from dataclasses import dataclass

@dataclass
class Config:
    subreddits: list; min_score: int; min_len: int; max_len: int
    hosts: dict; show: dict; gemini_api_key: str

def load(path="config.yaml") -> Config:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Config(
        subreddits=data["subreddits"], min_score=data["min_score"],
        min_len=data["min_len"], max_len=data["max_len"],
        hosts=data["hosts"], show=data["show"],
        gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
    )
```

Also create empty `src/__init__.py`, `tests/__init__.py`.

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add 14-drama-podcast
git commit -m "feat: scaffold project, config loader, data models"
```

---

### Task 2: State store (history + dedupe)

**Files:**
- Create: `src/state.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `state.State(path)` with `.seen_ids() -> set[str]`, `.is_seen(post_id) -> bool`, `.record_episode(post_id, title, audio_filename) -> None` (appends + persists), `.episodes() -> list[dict]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_state.py
from src.state import State

def test_dedupe_and_record(tmp_path):
    p = tmp_path / "history.json"
    st = State(str(p))
    assert st.is_seen("abc") is False
    st.record_episode("abc", "Title", "ep1.mp3")
    st2 = State(str(p))                 # reload from disk
    assert st2.is_seen("abc") is True
    assert st2.episodes()[0]["title"] == "Title"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_state.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.state'`

- [ ] **Step 3: Implement state**

```python
# src/state.py
import json, os

class State:
    def __init__(self, path="state/history.json"):
        self.path = path
        self.data = {"used_ids": [], "episodes": []}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                self.data = json.load(f)

    def seen_ids(self):
        return set(self.data["used_ids"])

    def is_seen(self, post_id):
        return post_id in self.seen_ids()

    def record_episode(self, post_id, title, audio_filename):
        self.data["used_ids"].append(post_id)
        self.data["episodes"].append({"id": post_id, "title": title, "audio": audio_filename})
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def episodes(self):
        return self.data["episodes"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_state.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/state.py tests/test_state.py
git commit -m "feat: history state store with dedupe"
```

---

### Task 3: Reddit source

**Files:**
- Create: `src/sources/__init__.py`, `src/sources/reddit.py`
- Test: `tests/test_reddit.py`

**Interfaces:**
- Consumes: `Config` (subreddits list).
- Produces: `reddit.fetch(subreddits: list[str], limit=25, http_get=requests.get) -> list[RawPost]`. `http_get` injectable for testing. Uses public JSON `https://www.reddit.com/r/<sub>/top.json?t=day&limit=<n>` with a `User-Agent` header (Reddit blocks default UA).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_reddit.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_reddit.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.sources.reddit'`

- [ ] **Step 3: Implement reddit source**

```python
# src/sources/reddit.py
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
```

Create empty `src/sources/__init__.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_reddit.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/sources tests/test_reddit.py
git commit -m "feat: reddit source fetch with nsfw/sticky filter"
```

---

### Task 4: Curate (filter + Gemini selection)

**Files:**
- Create: `src/curate.py`
- Test: `tests/test_curate.py`

**Interfaces:**
- Consumes: `list[RawPost]`, `State`, `Config`, a `select_fn` (injectable Gemini call).
- Produces: `curate.filter_candidates(posts, cfg, state) -> list[RawPost]` (score/len/dedupe). `curate.pick(candidates, select_fn) -> SelectedStory | None`. `select_fn(candidates: list[RawPost]) -> tuple[str, str]` returns `(chosen_id, reason)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_curate.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_curate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.curate'`

- [ ] **Step 3: Implement curate**

```python
# src/curate.py
from src.models import SelectedStory

def filter_candidates(posts, cfg, state):
    seen = state.seen_ids()
    out = []
    for p in posts:
        if p.id in seen: continue
        if p.score < cfg.min_score: continue
        if not (cfg.min_len <= len(p.body) <= cfg.max_len): continue
        out.append(p)
    return out

def pick(candidates, select_fn):
    if not candidates:
        return None
    chosen_id, reason = select_fn(candidates)
    for p in candidates:
        if p.id == chosen_id:
            return SelectedStory(post=p, reason=reason)
    return SelectedStory(post=candidates[0], reason=reason or "top scored")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_curate.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/curate.py tests/test_curate.py
git commit -m "feat: curate filter + injectable selection"
```

---

### Task 5: Script generation (Gemini Flash)

**Files:**
- Create: `src/script.py`
- Test: `tests/test_script.py`

**Interfaces:**
- Consumes: `SelectedStory`, `Config` (hosts, show), a `generate_fn` (injectable — returns JSON string).
- Produces: `script.build_prompt(story, hosts, show) -> str`. `script.generate(story, cfg, generate_fn) -> DialogueScript`. Also `script.gemini_generate_fn(api_key)` factory returning a real callable using `google-genai` `gemini-2.5-flash` with JSON response. Expected JSON: `{"title","description","tags":[...],"lines":[{"speaker","text"},...]}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_script.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_script.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.script'`

- [ ] **Step 3: Implement script**

```python
# src/script.py
import json
from src.models import DialogueScript, DialogueLine

def build_prompt(post, hosts, show):
    names = list(hosts.keys())
    return f"""You are the head writer for "{show.get('title','the show')}", a daily comedy
podcast where two hosts, {names[0]} and {names[1]}, react to internet drama stories.

Rewrite the Reddit story below as a natural, funny two-host dialogue. Rules:
- Do NOT read the story verbatim — react to and retell it in your own words (transformative).
- Open with a strong 10-second hook before revealing the topic.
- Alternate speakers naturally; add jokes, reactions, and banter.
- End with a short outro and a call to subscribe.
- Keep it 700-1200 words of spoken dialogue. English only.

Return ONLY valid JSON:
{{"title": <catchy episode title>, "description": <2-sentence show-notes with source credit to r/{post.subreddit}>,
  "tags": [<5 youtube tags>], "lines": [{{"speaker": "{names[0]}" or "{names[1]}", "text": <spoken line>}}, ...]}}

STORY (r/{post.subreddit}): "{post.title}"
{post.body}"""

def generate(story, cfg, generate_fn):
    raw = generate_fn(build_prompt(story.post, cfg.hosts, cfg.show))
    data = json.loads(raw)
    return DialogueScript(
        title=data["title"], description=data["description"], tags=data["tags"],
        lines=[DialogueLine(speaker=l["speaker"], text=l["text"]) for l in data["lines"]],
    )

def gemini_generate_fn(api_key):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key)
    def _fn(prompt):
        resp = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return resp.text
    return _fn
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_script.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/script.py tests/test_script.py
git commit -m "feat: dialogue script generation via injectable gemini fn"
```

---

### Task 6: Voice (Gemini multi-speaker TTS → WAV)

**Files:**
- Create: `src/voice.py`
- Test: `tests/test_voice.py`

**Interfaces:**
- Consumes: `DialogueScript`, `Config` (hosts→voice map), a `tts_fn` (injectable — returns raw PCM bytes).
- Produces: `voice.render_text(script) -> str` (joins lines as `"Max: ...\nIvy: ..."`). `voice.synthesize(script, cfg, tts_fn, out_path) -> str` writes a WAV file and returns path. `voice.pcm_to_wav(pcm_bytes, path, rate=24000)`. Also `voice.gemini_tts_fn(api_key, hosts)` factory returning callable `(text) -> pcm_bytes` using `gemini-2.5-flash-preview-tts` with `MultiSpeakerVoiceConfig`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_voice.py
import wave
from src import voice, models, config

def scr():
    return models.DialogueScript(title="T", description="d", tags=[],
        lines=[models.DialogueLine("Max", "Hello"), models.DialogueLine("Ivy", "Hi")])

def cfg():
    return config.Config(subreddits=[], min_score=0, min_len=0, max_len=0,
        hosts={"Max": "Charon", "Ivy": "Kore"}, show={}, gemini_api_key="")

def test_render_text_labels_speakers():
    assert voice.render_text(scr()) == "Max: Hello\nIvy: Hi"

def test_synthesize_writes_valid_wav(tmp_path):
    fake_tts = lambda text: b"\x00\x01" * 12000       # fake PCM
    out = tmp_path / "ep.wav"
    path = voice.synthesize(scr(), cfg(), tts_fn=fake_tts, out_path=str(out))
    with wave.open(path, "rb") as w:
        assert w.getframerate() == 24000
        assert w.getnchannels() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_voice.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.voice'`

- [ ] **Step 3: Implement voice**

```python
# src/voice.py
import wave

def render_text(script):
    return "\n".join(f"{l.speaker}: {l.text}" for l in script.lines)

def pcm_to_wav(pcm_bytes, path, rate=24000):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)          # 16-bit
        w.setframerate(rate)
        w.writeframes(pcm_bytes)
    return path

def synthesize(script, cfg, tts_fn, out_path):
    pcm = tts_fn(render_text(script))
    return pcm_to_wav(pcm, out_path)

def gemini_tts_fn(api_key, hosts):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key)
    speakers = [
        types.SpeakerVoiceConfig(
            speaker=name,
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)))
        for name, voice_name in hosts.items()
    ]
    def _fn(text):
        resp = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts", contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                        speaker_voice_configs=speakers))))
        return resp.candidates[0].content.parts[0].inline_data.data
    return _fn
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_voice.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/voice.py tests/test_voice.py
git commit -m "feat: multi-speaker TTS synth to wav via injectable tts fn"
```

---

### Task 7: Audio post-processing (ffmpeg → MP3)

**Files:**
- Create: `src/audio.py`
- Test: `tests/test_audio.py`

**Interfaces:**
- Consumes: WAV path, optional intro/outro paths.
- Produces: `audio.build_command(wav, out_mp3, intro=None, outro=None) -> list[str]` (ffmpeg argv with `loudnorm` -16 LUFS, concat intro+voice+outro). `audio.to_mp3(wav, out_mp3, intro=None, outro=None, runner=subprocess.run) -> str`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_audio.py
from src import audio

def test_command_has_loudnorm_and_mp3_out():
    cmd = audio.build_command("in.wav", "out.mp3")
    assert cmd[0] == "ffmpeg"
    assert any("loudnorm" in c for c in cmd)
    assert cmd[-1] == "out.mp3"

def test_to_mp3_invokes_runner():
    calls = {}
    def runner(cmd, check): calls["cmd"] = cmd; return 0
    audio.to_mp3("in.wav", "out.mp3", runner=runner)
    assert calls["cmd"][0] == "ffmpeg"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_audio.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.audio'`

- [ ] **Step 3: Implement audio**

```python
# src/audio.py
import subprocess

def build_command(wav, out_mp3, intro=None, outro=None):
    inputs, n = [], 0
    for f in [intro, wav, outro]:
        if f: inputs += ["-i", f]; n += 1
    if n > 1:
        streams = "".join(f"[{i}:a]" for i in range(n))
        fc = f"{streams}concat=n={n}:v=0:a=1[c];[c]loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    else:
        fc = "[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    return ["ffmpeg", "-y", *inputs, "-filter_complex", fc,
            "-map", "[a]", "-c:a", "libmp3lame", "-b:a", "128k", out_mp3]

def to_mp3(wav, out_mp3, intro=None, outro=None, runner=subprocess.run):
    runner(build_command(wav, out_mp3, intro, outro), check=True)
    return out_mp3
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_audio.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/audio.py tests/test_audio.py
git commit -m "feat: ffmpeg audio mastering (loudnorm + intro/outro concat)"
```

---

### Task 8: Video render (ffmpeg → MP4)

**Files:**
- Create: `src/video.py`
- Test: `tests/test_video.py`

**Interfaces:**
- Consumes: MP3 path, cover image path.
- Produces: `video.build_command(mp3, cover, out_mp4) -> list[str]` (static cover + showwaves overlay, `-shortest`). `video.to_mp4(mp3, cover, out_mp4, runner=subprocess.run) -> str`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_video.py
from src import video

def test_command_uses_cover_and_shortest():
    cmd = video.build_command("ep.mp3", "cover.png", "ep.mp4")
    assert "-shortest" in cmd
    assert "cover.png" in cmd
    assert cmd[-1] == "ep.mp4"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_video.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.video'`

- [ ] **Step 3: Implement video**

```python
# src/video.py
import subprocess

def build_command(mp3, cover, out_mp4):
    return ["ffmpeg", "-y", "-loop", "1", "-i", cover, "-i", mp3,
            "-filter_complex",
            "[1:a]showwaves=s=1280x200:mode=line:colors=white[wave];"
            "[0:v]scale=1280:720[bg];[bg][wave]overlay=0:520[v]",
            "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-shortest", out_mp4]

def to_mp4(mp3, cover, out_mp4, runner=subprocess.run):
    runner(build_command(mp3, cover, out_mp4), check=True)
    return out_mp4
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_video.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/video.py tests/test_video.py
git commit -m "feat: ffmpeg video render (cover + waveform)"
```

---

### Task 9: RSS publishing

**Files:**
- Create: `src/publish/__init__.py`, `src/publish/rss.py`
- Test: `tests/test_rss.py`

**Interfaces:**
- Consumes: `Config` (show), `State.episodes()`, base_url.
- Produces: `rss.build_feed(show, episodes, base_url) -> str` (RSS 2.0 + iTunes XML as string). Episode dict shape: `{"id","title","audio","description","length_bytes","pub_date"}`. Uses `feedgen`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rss.py
from src.publish import rss

def test_build_feed_contains_items():
    show = {"title": "Petty Court", "author": "PC", "description": "d",
            "language": "en-us", "base_url": "https://x.github.io/pc", "cover": "cover.png"}
    eps = [{"id": "a", "title": "Ep 1", "audio": "ep1.mp3", "description": "n",
            "length_bytes": 1000, "pub_date": "2026-07-04T10:00:00+00:00"}]
    xml = rss.build_feed(show, eps, show["base_url"])
    assert "<rss" in xml
    assert "Ep 1" in xml
    assert "https://x.github.io/pc/ep1.mp3" in xml
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_rss.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.publish.rss'`

- [ ] **Step 3: Implement rss**

```python
# src/publish/rss.py
from feedgen.feed import FeedGenerator

def build_feed(show, episodes, base_url):
    fg = FeedGenerator()
    fg.load_extension("podcast")
    fg.title(show["title"]); fg.author({"name": show["author"]})
    fg.link(href=base_url, rel="alternate")
    fg.description(show["description"]); fg.language(show.get("language", "en-us"))
    fg.logo(f"{base_url}/{show['cover'].split('/')[-1]}")
    fg.podcast.itunes_author(show["author"])
    for ep in episodes:
        fe = fg.add_entry()
        fe.id(ep["id"]); fe.title(ep["title"]); fe.description(ep["description"])
        fe.pubDate(ep["pub_date"])
        fe.enclosure(f"{base_url}/{ep['audio']}", str(ep["length_bytes"]), "audio/mpeg")
    return fg.rss_str(pretty=True).decode("utf-8")
```

Create empty `src/publish/__init__.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_rss.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/publish/__init__.py src/publish/rss.py tests/test_rss.py
git commit -m "feat: RSS 2.0 + iTunes feed generation"
```

---

### Task 10: YouTube publishing

**Files:**
- Create: `src/publish/youtube.py`
- Test: `tests/test_youtube.py`

**Interfaces:**
- Consumes: MP4 path, `DialogueScript` (title/description/tags), OAuth creds from env.
- Produces: `youtube.build_body(script) -> dict` (snippet+status request body). `youtube.upload(mp4, script, service) -> str` (returns video id); `service` injectable (googleapiclient resource). `youtube.build_service(client_id, client_secret, refresh_token)` factory.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_youtube.py
from src.publish import youtube
from src import models

def scr():
    return models.DialogueScript(title="Ep 1", description="d", tags=["drama"], lines=[])

def test_body_has_title_and_private_status():
    body = youtube.build_body(scr())
    assert body["snippet"]["title"] == "Ep 1"
    assert body["snippet"]["tags"] == ["drama"]
    assert body["status"]["privacyStatus"] == "public"

def test_upload_calls_insert():
    calls = {}
    class Req:
        def execute(self): return {"id": "vid123"}
    class Videos:
        def insert(self, part, body, media_body): calls["part"] = part; return Req()
    class Service:
        def videos(self): return Videos()
    vid = youtube.upload("ep.mp4", scr(), service=Service())
    assert vid == "vid123"
    assert "snippet" in calls["part"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_youtube.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.publish.youtube'`

- [ ] **Step 3: Implement youtube**

```python
# src/publish/youtube.py
def build_body(script):
    return {
        "snippet": {"title": script.title[:100], "description": script.description,
                    "tags": script.tags, "categoryId": "24"},   # 24 = Entertainment
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }

def upload(mp4, script, service):
    from googleapiclient.http import MediaFileUpload
    media = MediaFileUpload(mp4, chunksize=-1, resumable=True) if mp4 else None
    req = service.videos().insert(part="snippet,status", body=build_body(script), media_body=media)
    return req.execute()["id"]

def build_service(client_id, client_secret, refresh_token):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials(
        None, refresh_token=refresh_token, client_id=client_id, client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.upload"])
    return build("youtube", "v3", credentials=creds)
```

Note: `test_upload_calls_insert` passes `mp4="ep.mp4"` which triggers `MediaFileUpload`; to keep the test hermetic, pass `mp4=None` in the test OR patch MediaFileUpload. Update the test's `upload` call to `youtube.upload(None, scr(), service=Service())`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_youtube.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/publish/youtube.py tests/test_youtube.py
git commit -m "feat: youtube upload via injectable service"
```

---

### Task 11: Orchestration (main.py)

**Files:**
- Create: `src/main.py`
- Test: (manual dry-run; covered by a smoke test with all fns mocked)

**Interfaces:**
- Consumes: every module above.
- Produces: `main.run(cfg, state, deps) -> dict` where `deps` bundles injectable fns (`fetch`, `select_fn`, `script_fn`, `tts_fn`, `runner`, `yt_service`) so the whole pipeline is testable. Real entrypoint `main.main()` wires production fns from env/config. Publish stage isolates YouTube failure from RSS.

- [ ] **Step 1: Write the failing smoke test**

```python
# tests/test_main.py
import json
from src import main, config, models
from src.state import State

def test_run_pipeline_happy_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "output").mkdir(); (tmp_path / "assets").mkdir()
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.main'`

- [ ] **Step 3: Implement main**

```python
# src/main.py
import os, logging
from datetime import datetime, timezone
from src import config, curate, script as script_mod, voice, audio, video
from src.state import State
from src.publish import rss, youtube

log = logging.getLogger("pettycourt")

def run(cfg, state, deps):
    posts = deps["fetch"](cfg.subreddits)
    candidates = curate.filter_candidates(posts, cfg, state)
    story = curate.pick(candidates, deps["select_fn"])
    if story is None:
        log.warning("No candidate story today")
        return {"episode_id": None}

    scr = script_mod.generate(story, cfg, deps["script_fn"])
    ep_id = story.post.id
    wav = f"output/{ep_id}.wav"; mp3 = f"output/{ep_id}.mp3"; mp4 = f"output/{ep_id}.mp4"
    voice.synthesize(scr, cfg, deps["tts_fn"], wav)
    audio.to_mp3(wav, mp3, intro="assets/intro.mp3" if os.path.exists("assets/intro.mp3") else None,
                 outro="assets/outro.mp3" if os.path.exists("assets/outro.mp3") else None,
                 runner=deps["runner"])
    video.to_mp4(mp3, cfg.show["cover"], mp4, runner=deps["runner"])

    state.record_episode(ep_id, scr.title, f"{ep_id}.mp3")

    # --- Publish: isolate failures per target ---
    length = os.path.getsize(mp3) if os.path.exists(mp3) else 0
    eps = [{"id": e["id"], "title": e["title"], "audio": e["audio"],
            "description": scr.description, "length_bytes": length,
            "pub_date": datetime.now(timezone.utc).isoformat()} for e in state.episodes()]
    try:
        feed = rss.build_feed(cfg.show, eps, cfg.show["base_url"])
        with open("output/feed.xml", "w", encoding="utf-8") as f:
            f.write(feed)
    except Exception:
        log.exception("RSS publish failed")
    if deps.get("yt_service") is not None:
        try:
            youtube.upload(mp4, scr, deps["yt_service"])
        except Exception:
            log.exception("YouTube publish failed")

    return {"episode_id": ep_id, "title": scr.title}

def main():
    logging.basicConfig(level=logging.INFO)
    cfg = config.load()
    state = State()
    from src.sources import reddit
    deps = dict(
        fetch=lambda subs: reddit.fetch(subs),
        select_fn=_gemini_select_fn(cfg),
        script_fn=script_mod.gemini_generate_fn(cfg.gemini_api_key),
        tts_fn=voice.gemini_tts_fn(cfg.gemini_api_key, cfg.hosts),
        runner=__import__("subprocess").run,
        yt_service=youtube.build_service(
            os.environ["YOUTUBE_CLIENT_ID"], os.environ["YOUTUBE_CLIENT_SECRET"],
            os.environ["YOUTUBE_REFRESH_TOKEN"]) if os.environ.get("YOUTUBE_REFRESH_TOKEN") else None,
    )
    result = run(cfg, state, deps)
    log.info("Done: %s", result)

def _gemini_select_fn(cfg):
    """Ask Gemini Flash to pick the most podcast-worthy candidate id."""
    fn = script_mod.gemini_generate_fn(cfg.gemini_api_key)
    import json
    def _select(candidates):
        listing = "\n".join(f"- id={p.id} | {p.title} | {p.body[:200]}" for p in candidates)
        prompt = ("Pick the single most entertaining story for a comedy drama podcast. "
                  'Return JSON {"id": <id>, "reason": <why>}.\n' + listing)
        data = json.loads(fn(prompt))
        return data["id"], data.get("reason", "")
    return _select

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py -v`
Expected: PASS

- [ ] **Step 5: Run full suite**

Run: `pytest -v`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: pipeline orchestration with per-target publish isolation"
```

---

### Task 12: GitHub Actions daily workflow

**Files:**
- Create: `.github/workflows/daily.yml`

**Interfaces:** none (CI). Runs `python -m src.main` daily; commits `output/feed.xml`, MP3s, and `state/history.json` back to repo so GitHub Pages serves them.

- [ ] **Step 1: Write workflow**

```yaml
# .github/workflows/daily.yml
name: Daily Episode
on:
  schedule: [{cron: "0 9 * * *"}]   # 09:00 UTC daily
  workflow_dispatch:
jobs:
  produce:
    runs-on: ubuntu-latest
    permissions: {contents: write}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.11"}
      - run: sudo apt-get update && sudo apt-get install -y ffmpeg
      - run: pip install -r 14-drama-podcast/requirements.txt
      - name: Produce episode
        working-directory: 14-drama-podcast
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          YOUTUBE_CLIENT_ID: ${{ secrets.YOUTUBE_CLIENT_ID }}
          YOUTUBE_CLIENT_SECRET: ${{ secrets.YOUTUBE_CLIENT_SECRET }}
          YOUTUBE_REFRESH_TOKEN: ${{ secrets.YOUTUBE_REFRESH_TOKEN }}
        run: python -m src.main
      - name: Commit outputs
        run: |
          cd 14-drama-podcast
          git config user.name "bot"; git config user.email "bot@users.noreply.github.com"
          git add output/feed.xml output/*.mp3 state/history.json || true
          git commit -m "episode $(date -u +%F)" || echo "nothing to commit"
          git push
```

- [ ] **Step 2: Verify locally (dry run)**

Run: `cd 14-drama-podcast && python -m src.main` (with `.env` populated, or expect graceful skip if no candidates).
Expected: produces `output/<id>.mp3`, `output/<id>.mp4`, `output/feed.xml`, updates `state/history.json`.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/daily.yml
git commit -m "ci: daily episode workflow"
```

---

## Manual one-time setup (out of code, documented for operator)

1. `python -m venv .venv` içinde `pip install -r requirements.txt`.
2. `assets/` içine `intro.mp3`, `outro.mp3`, `cover.png` (1400x1400 iTunes min) koy.
3. Google AI Studio'dan `GEMINI_API_KEY` al.
4. Google Cloud Console: YouTube Data API v3 etkinleştir → OAuth client (Desktop) → local script ile `youtube.upload` scope'lu refresh token üret → 3 değeri GHA Secrets'a ekle.
5. GitHub repo → Settings → Pages → branch/`14-drama-podcast/output` klasörünü yayınla → `base_url`'i `config.yaml`'a yaz.
6. Yayınlanan `feed.xml` URL'ini Spotify for Podcasters + Apple Podcasts Connect'e **bir kez** ekle.

---

## Self-Review Notları

- **Spec coverage:** Fetch(T3)/Curate(T4)/Script(T5)/Voice(T6)/Audio(T7)/Video(T8)/RSS(T9)/YouTube(T10)/Orchestration+hata izolasyonu(T11)/GHA(T12)/State-dedupe(T2)/Config-secrets(T1) — spec'in 9 modülü + orkestrasyon + CI karşılandı. Telif (transformative prompt T5), loudnorm -16 (T7), tek Gemini key (T5/T6), kısmi başarı izolasyonu (T11) global constraint'ler task'lara yansıdı.
- **Placeholder taraması:** Yok — her step'te tam kod.
- **Tip tutarlılığı:** `RawPost`/`SelectedStory`/`DialogueScript`/`DialogueLine` T1'de tanımlı, T3-T11'de aynı imzalarla kullanıldı. `select_fn`→`(id, reason)`, `script_fn`→JSON str, `tts_fn`→pcm bytes, `runner(cmd, check)` her yerde tutarlı.
- **Bilinen düzeltme:** T10 Step 3 notu — `test_upload_calls_insert` içinde `upload(None, ...)` çağır (MediaFileUpload'ı tetiklememek için).
```
