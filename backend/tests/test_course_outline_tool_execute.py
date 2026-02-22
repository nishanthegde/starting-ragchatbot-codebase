import sys
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parents[1]
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from search_tools import CourseOutlineTool  # noqa: E402


class StubOutlineStore:
    def __init__(self, outline):
        self.outline = outline
        self.calls = []

    def get_course_outline(self, course_name: str):
        self.calls.append(course_name)
        return self.outline


def test_execute_returns_not_found_for_missing_outline():
    store = StubOutlineStore(None)
    tool = CourseOutlineTool(store)

    result = tool.execute("MCP")

    assert result == "No course outline found matching 'MCP'."
    assert store.calls == ["MCP"]


def test_execute_formats_course_and_lesson_links_as_new_tab_anchors():
    store = StubOutlineStore(
        {
            "title": "MCP: Build Rich-Context AI Apps with Anthropic",
            "course_link": "https://www.example.com/mcp",
            "lessons": [
                {
                    "lesson_number": 1,
                    "lesson_title": "Introduction",
                    "lesson_link": "https://www.example.com/mcp/lesson-1",
                }
            ],
        }
    )
    tool = CourseOutlineTool(store)

    result = tool.execute("MCP")

    assert (
        'Course Link: <a href="https://www.example.com/mcp" target="_blank" '
        'rel="noopener noreferrer">https://www.example.com/mcp</a>'
    ) in result
    assert (
        '<a href="https://www.example.com/mcp/lesson-1" target="_blank" '
        'rel="noopener noreferrer">(Link)</a>'
    ) in result


def test_execute_leaves_invalid_course_link_as_na():
    store = StubOutlineStore(
        {
            "title": "Unsafe Course",
            "course_link": "javascript:alert(1)",
            "lessons": [],
        }
    )
    tool = CourseOutlineTool(store)

    result = tool.execute("Unsafe")

    assert "Course Link: N/A" in result
    assert "<a href=" not in result
