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
