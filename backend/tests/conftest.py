import asyncio
from typing import Any

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)
    session_id: str | None = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
    session_id: str


class CourseStats(BaseModel):
    total_courses: int
    course_titles: list[str]


class StubSessionManager:
    def __init__(self):
        self.sessions: dict[str, list[dict[str, str]]] = {}
        self._counter = 0

    def create_session(self) -> str:
        self._counter += 1
        session_id = f"session_{self._counter}"
        self.sessions[session_id] = []
        return session_id

    def delete_session(self, session_id: str) -> bool:
        return self.sessions.pop(session_id, None) is not None


class StubRAGSystem:
    def __init__(self, course_analytics: dict[str, Any]):
        self.session_manager = StubSessionManager()
        self.query_result: tuple[str, list[str]] = ("", [])
        self.query_error: Exception | None = None
        self.analytics_error: Exception | None = None
        self.query_calls: list[dict[str, str]] = []
        self.course_analytics = course_analytics

    def query(self, query: str, session_id: str) -> tuple[str, list[str]]:
        self.query_calls.append({"query": query, "session_id": session_id})
        if self.query_error:
            raise self.query_error
        return self.query_result

    def get_course_analytics(self) -> dict[str, Any]:
        if self.analytics_error:
            raise self.analytics_error
        return self.course_analytics


@pytest.fixture
def sample_course_analytics() -> dict[str, Any]:
    return {
        "total_courses": 2,
        "course_titles": [
            "MCP: Build Rich-Context AI Apps with Anthropic",
            "Build AI Chatbots with RAG",
        ],
    }


@pytest.fixture
def sample_query_result() -> tuple[str, list[str]]:
    return (
        "Batching combines multiple operations into one request.",
        ["Mastering MCP - Lesson 2"],
    )


@pytest.fixture
def rag_stub(
    sample_course_analytics: dict[str, Any],
    sample_query_result: tuple[str, list[str]],
) -> StubRAGSystem:
    rag = StubRAGSystem(sample_course_analytics)
    rag.query_result = sample_query_result
    return rag


@pytest.fixture
def api_app(rag_stub: StubRAGSystem) -> FastAPI:
    app = FastAPI(title="Course Materials RAG Test App")

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id or rag_stub.session_manager.create_session()
            answer, sources = await asyncio.wait_for(
                asyncio.to_thread(rag_stub.query, request.query, session_id),
                timeout=5,
            )
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail=(
                    "The request timed out while generating a response. "
                    "Please try again."
                ),
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag_stub.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head><meta charset="UTF-8"><title>Course Materials Assistant</title></head>
        <body><h1>Course Materials Assistant</h1></body>
        </html>
        """

    return app


@pytest.fixture
def api_client(api_app: FastAPI):
    with TestClient(api_app) as client:
        yield client
