from typing import List, Optional

import anthropic


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    MAX_TOOL_ROUNDS = 2
    TOOL_FAILURE_FALLBACK = "I hit a retrieval issue while processing that request."

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to tools for course information.

Search Tool Usage:
- Use tools **only** for course-specific questions
- Use `search_course_content` for questions about specific lesson/content details
- Use `get_course_outline` for syllabus, outline, lesson-list, or curriculum-structure questions
- Use at most one tool call per round, with up to 2 rounds total when needed
- Synthesize tool results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives
- After using tools, provide a final direct answer to the user's question

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without tools
- **Course-specific questions**: Use the relevant tool first, then answer
- **Outline-related questions**: Return course title, course link, and every lesson with lesson number and lesson title; include `(Link)` after each lesson when lesson URL is available
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(
        self, api_key: str, model: str, timeout_seconds: float, max_retries: int
    ):
        self.client = anthropic.Anthropic(
            api_key=api_key, timeout=timeout_seconds, max_retries=max_retries
        )
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        messages = [{"role": "user", "content": query}]
        tools_enabled = bool(tools and tool_manager)

        if not tools_enabled:
            response = self._create_response(messages, system_content)
            return self._extract_text_response(response)

        completed_tool_rounds = 0
        while completed_tool_rounds < self.MAX_TOOL_ROUNDS:
            response = self._create_response(messages, system_content, tools)
            tool_calls = [
                block
                for block in response.content
                if getattr(block, "type", None) == "tool_use"
            ]

            if not tool_calls:
                return self._extract_text_response(response)

            messages.append({"role": "assistant", "content": response.content})

            try:
                tool_results = self._execute_tool_calls(tool_calls, tool_manager)
            except Exception:
                return self.TOOL_FAILURE_FALLBACK

            messages.append({"role": "user", "content": tool_results})
            completed_tool_rounds += 1

        final_response = self._create_response(messages, system_content)
        return self._extract_text_response(final_response)

    def _create_response(
        self, messages, system_content: str, tools: Optional[List] = None
    ):
        api_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content,
        }

        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        return self.client.messages.create(**api_params)

    def _execute_tool_calls(self, tool_calls, tool_manager):
        tool_results = []
        for tool_call in tool_calls:
            tool_result = tool_manager.execute_tool(tool_call.name, **tool_call.input)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": tool_result,
                }
            )
        return tool_results

    def _extract_text_response(self, response) -> str:
        for content_block in response.content:
            if getattr(content_block, "type", None) == "text":
                return content_block.text
        return ""
