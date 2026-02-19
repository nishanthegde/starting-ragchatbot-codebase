import sys
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from session_manager import SessionManager  # noqa: E402


def test_delete_session_removes_existing_session():
    manager = SessionManager()
    session_id = manager.create_session()
    manager.add_exchange(
        session_id, "What is RAG?", "RAG is retrieval-augmented generation."
    )

    assert session_id in manager.sessions
    assert manager.get_conversation_history(session_id) is not None

    deleted = manager.delete_session(session_id)

    assert deleted is True
    assert session_id not in manager.sessions
    assert manager.get_conversation_history(session_id) is None


def test_delete_session_returns_false_for_unknown_session():
    manager = SessionManager()

    deleted = manager.delete_session("session_does_not_exist")

    assert deleted is False
