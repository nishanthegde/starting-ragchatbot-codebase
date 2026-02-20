import sys
import copy
from pathlib import Path
from types import SimpleNamespace

BACKEND_PATH = Path(__file__).resolve().parents[1]
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from ai_generator import AIGenerator  # noqa: E402


class StubMessagesAPI:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        return self.responses.pop(0)


class StubAnthropicClient:
    def __init__(self, responses):
        self.messages = StubMessagesAPI(responses)


class StubToolManager:
    def __init__(self, fail: bool = False):
        self.calls = []
        self.fail = fail

    def execute_tool(self, tool_name: str, **kwargs):
        self.calls.append((tool_name, kwargs))
        if self.fail:
            raise RuntimeError("tool execution failed")
        return f"tool-result-{len(self.calls)}-{tool_name}"


def build_generator_with_stub_client(responses):
    generator = object.__new__(AIGenerator)
    generator.base_params = {"model": "test-model", "temperature": 0, "max_tokens": 800}
    generator.client = StubAnthropicClient(responses)
    return generator


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


def build_text_response(text: str):
    return SimpleNamespace(
        stop_reason="end_turn",
        content=[SimpleNamespace(type="text", text=text)],
    )


def test_generate_response_allows_two_sequential_tool_rounds_then_final_answer():
    first_round_response = build_tool_use_response(
        "get_course_outline", {"course_name": "Course X"}, "toolu_1"
    )
    second_round_response = build_tool_use_response(
        "search_course_content", {"query": "lesson 4 topic"}, "toolu_2"
    )
    final_response = build_text_response(
        "Course Y discusses the same topic as lesson 4."
    )

    generator = build_generator_with_stub_client(
        [first_round_response, second_round_response, final_response]
    )
    tool_manager = StubToolManager()
    tools = [
        {
            "name": "get_course_outline",
            "description": "Get course outline",
            "input_schema": {"type": "object"},
        },
        {
            "name": "search_course_content",
            "description": "Search content",
            "input_schema": {"type": "object"},
        },
    ]

    response_text = generator.generate_response(
        query="Find a course matching lesson 4 topic from Course X.",
        tools=tools,
        tool_manager=tool_manager,
    )

    assert response_text == "Course Y discusses the same topic as lesson 4."
    assert tool_manager.calls == [
        ("get_course_outline", {"course_name": "Course X"}),
        ("search_course_content", {"query": "lesson 4 topic"}),
    ]

    first_call, second_call, third_call = generator.client.messages.calls
    assert first_call["tools"] == tools
    assert second_call["tools"] == tools
    assert first_call["tool_choice"] == {"type": "auto"}
    assert second_call["tool_choice"] == {"type": "auto"}
    assert "tools" not in third_call

    assert second_call["messages"][-1]["role"] == "user"
    assert second_call["messages"][-1]["content"][0]["type"] == "tool_result"
    assert second_call["messages"][-1]["content"][0]["tool_use_id"] == "toolu_1"

    assert third_call["messages"][-1]["role"] == "user"
    assert third_call["messages"][-1]["content"][0]["type"] == "tool_result"
    assert third_call["messages"][-1]["content"][0]["tool_use_id"] == "toolu_2"


def test_generate_response_stops_when_round_response_has_no_tool_use():
    first_round_response = build_tool_use_response(
        "search_course_content", {"query": "lesson 5 summary"}, "toolu_123"
    )
    second_round_response = build_text_response("Lesson 5 covered batching tradeoffs.")

    generator = build_generator_with_stub_client(
        [first_round_response, second_round_response]
    )
    tool_manager = StubToolManager()
    tools = [{"name": "search_course_content", "input_schema": {"type": "object"}}]

    response_text = generator.generate_response(
        query="What was covered in lesson 5?",
        tools=tools,
        tool_manager=tool_manager,
    )

    assert response_text == "Lesson 5 covered batching tradeoffs."
    assert tool_manager.calls == [
        ("search_course_content", {"query": "lesson 5 summary"})
    ]
    assert len(generator.client.messages.calls) == 2
    assert generator.client.messages.calls[1]["tools"] == tools


def test_generate_response_stops_on_tool_failure_with_fallback():
    first_round_response = build_tool_use_response(
        "search_course_content", {"query": "lesson 5 summary"}, "toolu_fail"
    )
    generator = build_generator_with_stub_client(
        [first_round_response, build_text_response("unused")]
    )
    tool_manager = StubToolManager(fail=True)

    response_text = generator.generate_response(
        query="What was covered in lesson 5?",
        tools=[{"name": "search_course_content", "input_schema": {"type": "object"}}],
        tool_manager=tool_manager,
    )

    assert response_text == AIGenerator.TOOL_FAILURE_FALLBACK
    assert len(generator.client.messages.calls) == 1
    assert tool_manager.calls == [
        ("search_course_content", {"query": "lesson 5 summary"})
    ]


def test_generate_response_enforces_two_round_limit():
    first_round_response = build_tool_use_response(
        "search_course_content", {"query": "topic from lesson 4"}, "toolu_1"
    )
    second_round_response = build_tool_use_response(
        "search_course_content", {"query": "related courses"}, "toolu_2"
    )
    forced_final_response = build_text_response(
        "Course Y and Course Z both discuss that lesson topic."
    )
    unused_extra_response = build_tool_use_response(
        "search_course_content", {"query": "unused third tool call"}, "toolu_3"
    )

    generator = build_generator_with_stub_client(
        [
            first_round_response,
            second_round_response,
            forced_final_response,
            unused_extra_response,
        ]
    )
    tool_manager = StubToolManager()
    tools = [{"name": "search_course_content", "input_schema": {"type": "object"}}]

    response_text = generator.generate_response(
        query="Find courses with the same topic as lesson 4.",
        tools=tools,
        tool_manager=tool_manager,
    )

    assert response_text == "Course Y and Course Z both discuss that lesson topic."
    assert len(tool_manager.calls) == 2
    assert len(generator.client.messages.calls) == 3

    first_call, second_call, third_call = generator.client.messages.calls
    assert first_call["tools"] == tools
    assert second_call["tools"] == tools
    assert "tools" not in third_call
    assert len(generator.client.messages.responses) == 1
