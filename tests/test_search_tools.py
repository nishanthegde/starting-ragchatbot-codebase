import sys
from pathlib import Path
from types import SimpleNamespace

BACKEND_PATH = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from search_tools import CourseSearchTool  # noqa: E402


class StubStore:
    def __init__(self, links_by_key=None):
        self.links_by_key = links_by_key or {}

    def get_lesson_link(self, course_title: str, lesson_number: int):
        return self.links_by_key.get((course_title, lesson_number))


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
