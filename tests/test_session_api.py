import importlib
import sys
from pathlib import Path
from types import ModuleType

import pytest
from fastapi.testclient import TestClient

BACKEND_PATH = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))


class StubSessionManager:
    def __init__(self):
        self.sessions = {}
        self.session_counter = 0

    def create_session(self):
        self.session_counter += 1
        session_id = f"session_{self.session_counter}"
        self.sessions[session_id] = []
        return session_id

    def delete_session(self, session_id):
        return self.sessions.pop(session_id, None) is not None


class StubRAGSystem:
    def __init__(self, _config):
        self.session_manager = StubSessionManager()

    def add_course_folder(self, _folder_path, clear_existing=False):
        return 0, 0

    def get_course_analytics(self):
        return {"total_courses": 0, "course_titles": []}

    def query(self, _query, _session_id=None):
        return "", []


@pytest.fixture
def api_client(monkeypatch):
    fake_rag_module = ModuleType("rag_system")
    fake_rag_module.RAGSystem = StubRAGSystem
    monkeypatch.setitem(sys.modules, "rag_system", fake_rag_module)
    monkeypatch.chdir(BACKEND_PATH)

    sys.modules.pop("app", None)
    app_module = importlib.import_module("app")

    with TestClient(app_module.app) as client:
        yield client

    sys.modules.pop("app", None)


def test_create_new_session_without_previous_session(api_client):
    response = api_client.post("/api/session/new", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"]
    assert payload["cleared_previous"] is False


def test_create_new_session_clears_previous_session(api_client):
    first_response = api_client.post("/api/session/new", json={})
    first_payload = first_response.json()

    response = api_client.post(
        "/api/session/new",
        json={"previous_session_id": first_payload["session_id"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"]
    assert payload["session_id"] != first_payload["session_id"]
    assert payload["cleared_previous"] is True
