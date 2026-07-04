from src import video


def test_command_uses_cover_and_shortest():
    cmd = video.build_command("ep.mp3", "cover.png", "ep.mp4")
    assert "-shortest" in cmd
    assert "cover.png" in cmd
    assert cmd[-1] == "ep.mp4"
