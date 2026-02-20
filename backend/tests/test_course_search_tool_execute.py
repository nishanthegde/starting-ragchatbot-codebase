import sys
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parents[1]
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from search_tools import CourseSearchTool  # noqa: E402
from vector_store import SearchResults  # noqa: E402


class StubVectorStore:
    def __init__(self, result: SearchResults):
        self.result = result
        self.search_calls = []
        self.lesson_links = {}

    def search(self, query: str, course_name=None, lesson_number=None):
        self.search_calls.append(
            {
                "query": query,
                "course_name": course_name,
                "lesson_number": lesson_number,
            }
        )
        return self.result

    def get_lesson_link(self, course_title: str, lesson_number: int):
        return self.lesson_links.get((course_title, lesson_number))


def test_execute_returns_search_error_from_store():
    store = StubVectorStore(SearchResults.empty("Search error: backend unavailable"))
    tool = CourseSearchTool(store)

    result = tool.execute(query="What is MCP?")

    assert result == "Search error: backend unavailable"
    assert store.search_calls == [
        {"query": "What is MCP?", "course_name": None, "lesson_number": None}
    ]


def test_execute_returns_filtered_no_results_message():
    store = StubVectorStore(
        SearchResults(documents=[], metadata=[], distances=[], error=None)
    )
    tool = CourseSearchTool(store)

    result = tool.execute(
        query="What is batching?", course_name="MCP", lesson_number=2
    )

    assert result == "No relevant content found in course 'MCP' in lesson 2."
    assert store.search_calls == [
        {"query": "What is batching?", "course_name": "MCP", "lesson_number": 2}
    ]


def test_execute_formats_results_and_populates_sources():
    store = StubVectorStore(
        SearchResults(
            documents=["Batch requests reduce round trips."],
            metadata=[{"course_title": "Mastering MCP", "lesson_number": 2}],
            distances=[0.1],
            error=None,
        )
    )
    store.lesson_links[("Mastering MCP", 2)] = (
        "https://example.com/mastering-mcp/lesson-2"
    )
    tool = CourseSearchTool(store)

    result = tool.execute(query="Explain batching")

    assert "[Mastering MCP - Lesson 2]" in result
    assert "Batch requests reduce round trips." in result
    assert len(tool.last_sources) == 1
    assert "href=" in tool.last_sources[0]
    assert "Mastering MCP - Lesson 2" in tool.last_sources[0]
