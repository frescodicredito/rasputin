import time

from rasputin.sessions import Session, SessionManager


def test_create_single_session():
    mgr = SessionManager(ttl_minutes=60)
    session = mgr.get_or_create(None, type="single", models=["gemini/gemini-2.5-flash"])
    assert session.id.startswith("ask-")
    assert session.type == "single"
    assert session.models == ["gemini/gemini-2.5-flash"]


def test_create_council_session():
    mgr = SessionManager(ttl_minutes=60)
    session = mgr.get_or_create(None, type="council", models=["a", "b", "c"])
    assert session.id.startswith("council-")
    assert len(session.models) == 3


def test_get_existing_session():
    mgr = SessionManager(ttl_minutes=60)
    s1 = mgr.get_or_create(None, type="single", models=["m"])
    s2 = mgr.get_or_create(s1.id, type="single", models=["m"])
    assert s1.id == s2.id


def test_session_messages():
    s = Session(id="test", type="single", models=["m1"])
    s.add_user_message("hello")
    s.add_assistant_message("m1", "world")
    msgs = s.get_messages("m1")
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"


def test_session_expiry():
    mgr = SessionManager(ttl_minutes=0)
    s = mgr.get_or_create(None, type="single", models=["m"])
    time.sleep(0.1)
    assert mgr.get(s.id) is None


def test_list_active():
    mgr = SessionManager(ttl_minutes=60)
    mgr.get_or_create(None, type="single", models=["a"])
    mgr.get_or_create(None, type="council", models=["b", "c"])
    active = mgr.list_active()
    assert len(active) == 2


def test_close_session():
    mgr = SessionManager(ttl_minutes=60)
    s = mgr.get_or_create(None, type="single", models=["m"])
    mgr.close(s.id)
    assert mgr.get(s.id) is None


def test_to_dict():
    s = Session(id="test", type="single", models=["m1"])
    d = s.to_dict()
    assert d["id"] == "test"
    assert d["type"] == "single"
    assert "age_minutes" in d


def test_session_manager_evicts_lru_over_cap():
    mgr = SessionManager(ttl_minutes=60, max_sessions=2)
    s1 = mgr.get_or_create(None, type="council", models=["m"])
    s2 = mgr.get_or_create(None, type="council", models=["m"])

    now = time.time()
    s1.last_access = now - 10  # least recently accessed
    s2.last_access = now - 1

    s3 = mgr.get_or_create(None, type="council", models=["m"])

    assert mgr.get(s1.id) is None  # evicted
    assert mgr.get(s2.id) is not None
    assert mgr.get(s3.id) is not None
    assert len(mgr.list_active()) == 2
