def test_query_endpoint_creates_new_session_when_missing(api_client, rag_stub):
    response = api_client.post("/api/query", json={"query": "Explain batching"})

    assert response.status_code == 200
    payload = response.json()
    assert (
        payload["answer"] == "Batching combines multiple operations into one request."
    )
    assert payload["sources"] == ["Mastering MCP - Lesson 2"]
    assert payload["session_id"].startswith("session_")
    assert rag_stub.query_calls == [
        {"query": "Explain batching", "session_id": payload["session_id"]}
    ]


def test_query_endpoint_uses_provided_session_id(api_client, rag_stub):
    response = api_client.post(
        "/api/query",
        json={"query": "What was covered in lesson 5?", "session_id": "session_custom"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "session_custom"
    assert rag_stub.query_calls[-1] == {
        "query": "What was covered in lesson 5?",
        "session_id": "session_custom",
    }


def test_query_endpoint_returns_500_when_rag_raises(api_client, rag_stub):
    rag_stub.query_error = RuntimeError("RAG backend unavailable")

    response = api_client.post("/api/query", json={"query": "What is RAG?"})

    assert response.status_code == 500
    assert response.json() == {"detail": "RAG backend unavailable"}


def test_query_endpoint_rejects_invalid_payload(api_client):
    response = api_client.post("/api/query", json={"session_id": "missing_query"})

    assert response.status_code == 422


def test_courses_endpoint_returns_course_stats(api_client, sample_course_analytics):
    response = api_client.get("/api/courses")

    assert response.status_code == 200
    assert response.json() == sample_course_analytics


def test_courses_endpoint_returns_500_when_analytics_fail(api_client, rag_stub):
    rag_stub.analytics_error = RuntimeError("Analytics unavailable")

    response = api_client.get("/api/courses")

    assert response.status_code == 500
    assert response.json() == {"detail": "Analytics unavailable"}


def test_root_endpoint_returns_html_response(api_client):
    response = api_client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Course Materials Assistant" in response.text
