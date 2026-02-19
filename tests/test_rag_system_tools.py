import sys
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

import rag_system  # noqa: E402


class StubDocumentProcessor:
    def __init__(self, _chunk_size, _chunk_overlap):
        pass


class StubVectorStore:
    def __init__(self, _chroma_path, _embedding_model, _max_results):
        pass


class StubAIGenerator:
    def __init__(self, _api_key, _model, _timeout_seconds, _max_retries):
        pass


class StubSessionManager:
    def __init__(self, _max_history):
        pass


class StubConfig:
    CHUNK_SIZE = 512
    CHUNK_OVERLAP = 50
    CHROMA_PATH = "/tmp/chroma"
    EMBEDDING_MODEL = "fake-model"
    MAX_RESULTS = 5
    ANTHROPIC_API_KEY = "test-key"
    ANTHROPIC_MODEL = "test-model"
    ANTHROPIC_TIMEOUT_SECONDS = 10
    ANTHROPIC_MAX_RETRIES = 1
    MAX_HISTORY = 10


def test_rag_system_registers_content_and_outline_tools(monkeypatch):
    monkeypatch.setattr(rag_system, "DocumentProcessor", StubDocumentProcessor)
    monkeypatch.setattr(rag_system, "VectorStore", StubVectorStore)
    monkeypatch.setattr(rag_system, "AIGenerator", StubAIGenerator)
    monkeypatch.setattr(rag_system, "SessionManager", StubSessionManager)

    system = rag_system.RAGSystem(StubConfig())
    tool_names = {
        tool_definition["name"]
        for tool_definition in system.tool_manager.get_tool_definitions()
    }

    assert "search_course_content" in tool_names
    assert "get_course_outline" in tool_names
