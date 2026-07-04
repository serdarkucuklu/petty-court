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
