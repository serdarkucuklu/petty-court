import os, shutil, logging
from datetime import datetime, timezone
from src import config, curate, script as script_mod, voice, audio, video
from src.state import State
from src.publish import rss, youtube

log = logging.getLogger("pettycourt")

def run(cfg, state, deps):
    os.makedirs("output", exist_ok=True)
    posts = deps["fetch"](cfg.subreddits)
    candidates = curate.filter_candidates(posts, cfg, state)
    story = curate.pick(candidates, deps["select_fn"])
    if story is None:
        log.warning("No candidate story today")
        return {"episode_id": None}

    scr = script_mod.generate(story, cfg, deps["script_fn"])
    ep_id = story.post.id
    wav = f"output/{ep_id}.wav"; mp3 = f"output/{ep_id}.mp3"; mp4 = f"output/{ep_id}.mp4"

    # Core product: audio. A failure here is a genuine run failure.
    voice.synthesize(scr, cfg, deps["tts_fn"], wav)
    audio.to_mp3(wav, mp3, intro="assets/intro.mp3" if os.path.exists("assets/intro.mp3") else None,
                 outro="assets/outro.mp3" if os.path.exists("assets/outro.mp3") else None,
                 runner=deps["runner"])

    length = os.path.getsize(mp3) if os.path.exists(mp3) else 0
    pub_date = datetime.now(timezone.utc).isoformat()
    state.record_episode(ep_id, scr.title, f"{ep_id}.mp3",
                         description=scr.description, length_bytes=length, pub_date=pub_date)

    # --- Publish RSS (core podcast; isolated so a feed error can't kill the run) ---
    try:
        cover = cfg.show.get("cover")
        if cover and os.path.exists(cover):
            shutil.copy(cover, os.path.join("output", os.path.basename(cover)))
        eps = [{"id": e["id"], "title": e["title"], "audio": e["audio"],
                "description": e.get("description", ""),
                "length_bytes": e.get("length_bytes", 0),
                "pub_date": e.get("pub_date", "")} for e in state.episodes()]
        feed = rss.build_feed(cfg.show, eps, cfg.show["base_url"])
        with open("output/feed.xml", "w", encoding="utf-8") as f:
            f.write(feed)
    except Exception:
        log.exception("RSS publish failed")

    # --- Video + YouTube (secondary; isolated so failure never affects the podcast) ---
    try:
        video.to_mp4(mp3, cfg.show["cover"], mp4, runner=deps["runner"])
        if deps.get("yt_service") is not None:
            youtube.upload(mp4, scr, deps["yt_service"])
    except Exception:
        log.exception("Video/YouTube publish failed")

    return {"episode_id": ep_id, "title": scr.title}

def main():
    logging.basicConfig(level=logging.INFO)
    cfg = config.load()
    state = State()
    from src.sources import reddit
    r_id = os.environ.get("REDDIT_CLIENT_ID"); r_sec = os.environ.get("REDDIT_CLIENT_SECRET")
    reddit_token = reddit.get_token(r_id, r_sec) if (r_id and r_sec) else None
    deps = dict(
        fetch=lambda subs: reddit.fetch(subs, token=reddit_token),
        select_fn=_gemini_select_fn(cfg),
        script_fn=script_mod.gemini_generate_fn(cfg.gemini_api_key),
        tts_fn=voice.gemini_tts_fn(cfg.gemini_api_key, cfg.hosts),
        runner=__import__("subprocess").run,
        yt_service=_yt_service_from_env(),
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

def _yt_service_from_env():
    cid = os.environ.get("YOUTUBE_CLIENT_ID")
    csec = os.environ.get("YOUTUBE_CLIENT_SECRET")
    tok = os.environ.get("YOUTUBE_REFRESH_TOKEN")
    if cid and csec and tok:
        return youtube.build_service(cid, csec, tok)
    return None

if __name__ == "__main__":
    main()
