import sys
from pathlib import Path
from types import SimpleNamespace

BACKEND_PATH = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from ai_generator import AIGenerator  # noqa: E402


class StubMessagesAPI:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


class StubAnthropicClient:
    def __init__(self, responses):
        self.messages = StubMessagesAPI(responses)


def build_tool_use_response(tool_name: str, tool_input: dict, tool_use_id: str):
    return SimpleNamespace(
        stop_reason="tool_use",
        content=[
            SimpleNamespace(
                type="tool_use",
                name=tool_name,
                input=tool_input,
                id=tool_use_id,
            )
        ],
    )


def test_system_prompt_includes_outline_tool_instructions():
    prompt = AIGenerator.SYSTEM_PROMPT

    assert "get_course_outline" in prompt
    assert "course title, course link, and every lesson" in prompt
    assert "lesson number and lesson title" in prompt
    assert "(Link)" in prompt


def test_outline_tool_result_is_returned_without_link_rewrite():
    generator = object.__new__(AIGenerator)
    generator.base_params = {"model": "test-model", "temperature": 0, "max_tokens": 800}
    generator.client = StubAnthropicClient(
        [
            build_tool_use_response(
                "get_course_outline", {"course_name": "MCP"}, "tool_1"
            )
        ]
    )

    class StubToolManager:
        def execute_tool(self, tool_name, **kwargs):
            assert tool_name == "get_course_outline"
            assert kwargs == {"course_name": "MCP"}
            return (
                "Lesson 1: Intro "
                '<a href="https://example.com/lesson-1" target="_blank" '
                'rel="noopener noreferrer">(Link)</a>'
            )

    result = generator.generate_response(
        query="Show outline",
        tools=[{"name": "get_course_outline", "input_schema": {"type": "object"}}],
        tool_manager=StubToolManager(),
    )

    assert 'href="https://example.com/lesson-1"' in result
    assert ">(Link)</a>" in result
    assert len(generator.client.messages.calls) == 1
