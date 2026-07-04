from dataclasses import dataclass, field

@dataclass
class RawPost:
    id: str
    subreddit: str
    title: str
    body: str
    score: int
    url: str
    created_utc: float

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
