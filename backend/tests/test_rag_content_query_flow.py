import sys
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parents[1]
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
        self.calls = []

    def generate_response(self, **kwargs):
        self.calls.append(kwargs)
        return "Batching combines multiple operations into one request."


class StubSessionManager:
    def __init__(self, _max_history):
        self.exchanges = []

    def get_conversation_history(self, _session_id: str):
        return "user: previous question\nassistant: previous answer"

    def add_exchange(self, session_id: str, query: str, response: str):
        self.exchanges.append((session_id, query, response))


class StubConfig:
    CHUNK_SIZE = 800
    CHUNK_OVERLAP = 100
    CHROMA_PATH = "/tmp/chroma"
    EMBEDDING_MODEL = "fake-model"
    MAX_RESULTS = 5
    ANTHROPIC_API_KEY = "test-key"
    ANTHROPIC_MODEL = "test-model"
    ANTHROPIC_TIMEOUT_SECONDS = 10
    ANTHROPIC_MAX_RETRIES = 1
    MAX_HISTORY = 3


def test_query_handles_content_question_and_returns_sources(monkeypatch):
    monkeypatch.setattr(rag_system, "DocumentProcessor", StubDocumentProcessor)
    monkeypatch.setattr(rag_system, "VectorStore", StubVectorStore)
    monkeypatch.setattr(rag_system, "AIGenerator", StubAIGenerator)
    monkeypatch.setattr(rag_system, "SessionManager", StubSessionManager)

    system = rag_system.RAGSystem(StubConfig())
    system.tool_manager.get_last_sources = lambda: ["Mastering MCP - Lesson 2"]

    response, sources = system.query(
        "Give me details from lesson 2 of Mastering MCP", session_id="session-1"
    )

    assert response == "Batching combines multiple operations into one request."
    assert sources == ["Mastering MCP - Lesson 2"]
    assert system.session_manager.exchanges == [
        (
            "session-1",
            "Give me details from lesson 2 of Mastering MCP",
            "Batching combines multiple operations into one request.",
        )
    ]


def test_query_handles_content_query_pipeline_errors_without_raising(monkeypatch):
    monkeypatch.setattr(rag_system, "DocumentProcessor", StubDocumentProcessor)
    monkeypatch.setattr(rag_system, "VectorStore", StubVectorStore)
    monkeypatch.setattr(rag_system, "AIGenerator", StubAIGenerator)
    monkeypatch.setattr(rag_system, "SessionManager", StubSessionManager)

    system = rag_system.RAGSystem(StubConfig())

    def fail_generate_response(**_kwargs):
        raise RuntimeError("tool execution failed")

    system.ai_generator.generate_response = fail_generate_response

    response, sources = system.query(
        "What was covered in lesson 5 of the MCP course?", session_id="session-1"
    )

    assert "couldn't process that course-content request" in response
    assert sources == []
