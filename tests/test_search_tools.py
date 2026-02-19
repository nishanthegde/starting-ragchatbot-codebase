import sys
from pathlib import Path
from types import SimpleNamespace

BACKEND_PATH = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from search_tools import CourseOutlineTool, CourseSearchTool  # noqa: E402


class StubStore:
    def __init__(self, links_by_key=None, outlines_by_name=None):
        self.links_by_key = links_by_key or {}
        self.outlines_by_name = outlines_by_name or {}

    def get_lesson_link(self, course_title: str, lesson_number: int):
        return self.links_by_key.get((course_title, lesson_number))

    def get_course_outline(self, course_name: str):
        return self.outlines_by_name.get(course_name)


def make_results(documents, metadata):
    return SimpleNamespace(documents=documents, metadata=metadata)


def test_format_results_includes_clickable_lesson_source():
    tool = CourseSearchTool(
        StubStore({("Course A", 2): "https://example.com/course-a/lesson-2"})
    )
    results = make_results(
        ["Lesson content"],
        [{"course_title": "Course A", "lesson_number": 2}],
    )

    tool._format_results(results)

    source = tool.last_sources[0]
    assert '<a href="https://example.com/course-a/lesson-2"' in source
    assert 'target="_blank"' in source
    assert 'rel="noopener noreferrer"' in source
    assert ">Course A - Lesson 2</a>" in source


def test_format_results_keeps_plain_source_when_no_link():
    tool = CourseSearchTool(StubStore())
    results = make_results(
        ["Lesson content"],
        [{"course_title": "Course A", "lesson_number": 2}],
    )

    tool._format_results(results)

    source = tool.last_sources[0]
    assert source == "Course A - Lesson 2"
    assert "<a " not in source


def test_format_results_rejects_non_http_scheme():
    tool = CourseSearchTool(StubStore({("Course A", 2): "javascript:alert('xss')"}))
    results = make_results(
        ["Lesson content"],
        [{"course_title": "Course A", "lesson_number": 2}],
    )

    tool._format_results(results)

    source = tool.last_sources[0]
    assert source == "Course A - Lesson 2"
    assert "<a " not in source


def test_format_results_deduplicates_sources_preserving_order():
    tool = CourseSearchTool(
        StubStore({("Course A", 2): "https://example.com/course-a/lesson-2"})
    )
    results = make_results(
        ["First chunk", "Second chunk"],
        [
            {"course_title": "Course A", "lesson_number": 2},
            {"course_title": "Course A", "lesson_number": 2},
        ],
    )

    formatted = tool._format_results(results)

    assert len(tool.last_sources) == 1
    assert formatted.count("[Course A - Lesson 2]") == 2


def test_get_course_outline_tool_returns_full_outline():
    tool = CourseOutlineTool(
        StubStore(
            outlines_by_name={
                "MCP": {
                    "title": "Mastering MCP",
                    "course_link": "https://example.com/mcp",
                    "lessons": [
                        {
                            "lesson_number": 1,
                            "lesson_title": "Introduction",
                            "lesson_link": "https://example.com/mcp/intro",
                        },
                        {
                            "lesson_number": 2,
                            "lesson_title": "Tool Basics",
                            "lesson_link": "https://example.com/mcp/tools",
                        },
                    ],
                }
            }
        )
    )

    result = tool.execute(course_name="MCP")

    assert "Course Title: Mastering MCP" in result
    assert "Course Link: https://example.com/mcp" in result
    assert (
        '- Lesson 1: Introduction <a href="https://example.com/mcp/intro"'
        ' target="_blank" rel="noopener noreferrer">(Link)</a>' in result
    )
    assert (
        '- Lesson 2: Tool Basics <a href="https://example.com/mcp/tools"'
        ' target="_blank" rel="noopener noreferrer">(Link)</a>' in result
    )


def test_get_course_outline_tool_handles_course_not_found():
    tool = CourseOutlineTool(StubStore())

    result = tool.execute(course_name="Unknown Course")

    assert result == "No course outline found matching 'Unknown Course'."


def test_get_course_outline_tool_handles_missing_course_link():
    tool = CourseOutlineTool(
        StubStore(
            outlines_by_name={
                "No Link Course": {
                    "title": "No Link Course",
                    "course_link": None,
                    "lessons": [
                        {"lesson_number": 1, "lesson_title": "Start Here"},
                    ],
                }
            }
        )
    )

    result = tool.execute(course_name="No Link Course")

    assert "Course Link: N/A" in result
    assert "- Lesson 1: Start Here" in result


def test_get_course_outline_tool_ignores_unsafe_lesson_link():
    tool = CourseOutlineTool(
        StubStore(
            outlines_by_name={
                "Unsafe Link Course": {
                    "title": "Unsafe Link Course",
                    "course_link": "https://example.com/course",
                    "lessons": [
                        {
                            "lesson_number": 1,
                            "lesson_title": "Start Here",
                            "lesson_link": "javascript:alert('xss')",
                        },
                    ],
                }
            }
        )
    )

    result = tool.execute(course_name="Unsafe Link Course")

    assert "- Lesson 1: Start Here" in result
    assert "Link</a>" not in result
