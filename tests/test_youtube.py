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
    vid = youtube.upload(None, scr(), service=Service())
    assert vid == "vid123"
    assert "snippet" in calls["part"]
