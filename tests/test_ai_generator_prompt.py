import sys
from pathlib import Path
from types import SimpleNamespace

BACKEND_PATH = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from ai_generator import AIGenerator  # noqa: E402


def test_system_prompt_includes_outline_tool_instructions():
    prompt = AIGenerator.SYSTEM_PROMPT

    assert "get_course_outline" in prompt
    assert "course title, course link, and every lesson" in prompt
    assert "lesson number and lesson title" in prompt
    assert "(Link)" in prompt


def test_outline_tool_result_is_returned_without_link_rewrite():
    generator = object.__new__(AIGenerator)

    initial_response = SimpleNamespace(
        content=[
            SimpleNamespace(
                type="tool_use",
                name="get_course_outline",
                input={"course_name": "MCP"},
                id="tool_1",
            )
        ]
    )
    base_params = {
        "messages": [{"role": "user", "content": "Show outline"}],
        "system": "system",
    }

    class StubToolManager:
        def execute_tool(self, _tool_name, **_kwargs):
            return (
                "Lesson 1: Intro "
                '<a href="https://example.com/lesson-1" target="_blank" '
                'rel="noopener noreferrer">(Link)</a>'
            )

    result = generator._handle_tool_execution(
        initial_response, base_params, StubToolManager()
    )

    assert 'href="https://example.com/lesson-1"' in result
    assert ">(Link)</a>" in result
