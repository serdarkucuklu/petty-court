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
