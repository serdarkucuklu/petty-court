import os
import yaml
from dataclasses import dataclass

@dataclass
class Config:
    subreddits: list
    min_score: int
    min_len: int
    max_len: int
    hosts: dict
    show: dict
    gemini_api_key: str

def load(path="config.yaml") -> Config:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Config(
        subreddits=data["subreddits"],
        min_score=data["min_score"],
        min_len=data["min_len"],
        max_len=data["max_len"],
        hosts=data["hosts"],
        show=data["show"],
        gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
    )
