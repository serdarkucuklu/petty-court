from src.state import State

def test_dedupe_and_record(tmp_path):
    p = tmp_path / "history.json"
    st = State(str(p))
    assert st.is_seen("abc") is False
    st.record_episode("abc", "Title", "ep1.mp3")
    st2 = State(str(p))                 # reload from disk
    assert st2.is_seen("abc") is True
    assert st2.episodes()[0]["title"] == "Title"

def test_record_is_idempotent(tmp_path):
    st = State(str(tmp_path / "h.json"))
    st.record_episode("dup", "T1", "a.mp3")
    st.record_episode("dup", "T2", "a.mp3")   # same id again
    assert len(st.episodes()) == 1
    assert st.episodes()[0]["title"] == "T1"   # first write wins
