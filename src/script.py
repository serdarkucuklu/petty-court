import json
from src.models import DialogueScript, DialogueLine
from src.gemini_retry import call_with_retry

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
        resp = call_with_retry(lambda: client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        ))
        return resp.text
    return _fn
