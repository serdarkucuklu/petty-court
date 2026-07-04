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
        if post_id in self.seen_ids():
            return
        self.data["used_ids"].append(post_id)
        self.data["episodes"].append({"id": post_id, "title": title, "audio": audio_filename})
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def episodes(self):
        return self.data["episodes"]
