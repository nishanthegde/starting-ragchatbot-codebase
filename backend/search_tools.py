import html
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from vector_store import SearchResults, VectorStore


class Tool(ABC):
    """Abstract base class for all tools"""

    @abstractmethod
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute the tool with given parameters"""
        pass


class CourseSearchTool(Tool):
    """Tool for searching course content with semantic course name matching"""

    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources = []  # Track sources from last search

    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        return {
            "name": "search_course_content",
            "description": "Search course materials with smart course name matching and lesson filtering",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for in the course content",
                    },
                    "course_name": {
                        "type": "string",
                        "description": "Course title (partial matches work, e.g. 'MCP', 'Introduction')",
                    },
                    "lesson_number": {
                        "type": "integer",
                        "description": "Specific lesson number to search within (e.g. 1, 2, 3)",
                    },
                },
                "required": ["query"],
            },
        }

    def execute(
        self,
        query: str,
        course_name: Optional[str] = None,
        lesson_number: Optional[int] = None,
    ) -> str:
        """
        Execute the search tool with given parameters.

        Args:
            query: What to search for
            course_name: Optional course filter
            lesson_number: Optional lesson filter

        Returns:
            Formatted search results or error message
        """

        # Use the vector store's unified search interface
        results = self.store.search(
            query=query, course_name=course_name, lesson_number=lesson_number
        )

        # Handle errors
        if results.error:
            return results.error

        # Handle empty results
        if results.is_empty():
            filter_info = ""
            if course_name:
                filter_info += f" in course '{course_name}'"
            if lesson_number:
                filter_info += f" in lesson {lesson_number}"
            return f"No relevant content found{filter_info}."

        # Format and return results
        return self._format_results(results)

    def _format_results(self, results: SearchResults) -> str:
        """Format search results with course and lesson context"""
        formatted = []
        sources = []  # Track sources for the UI
        seen_sources = set()

        for doc, meta in zip(results.documents, results.metadata):
            course_title = meta.get("course_title", "unknown")
            lesson_num = meta.get("lesson_number")

            # Build context header
            header = f"[{course_title}"
            if lesson_num is not None:
                header += f" - Lesson {lesson_num}"
            header += "]"

            # Track source for the UI
            source = course_title
            if lesson_num is not None:
                source += f" - Lesson {lesson_num}"

            source_entry = self._build_source_entry(course_title, lesson_num, source)
            if source_entry not in seen_sources:
                sources.append(source_entry)
                seen_sources.add(source_entry)

            formatted.append(f"{header}\n{doc}")

        # Store sources for retrieval
        self.last_sources = sources

        return "\n\n".join(formatted)

    def _build_source_entry(
        self, course_title: str, lesson_num: Optional[int], source_label: str
    ) -> str:
        """Build a source label with optional clickable lesson link."""
        escaped_label = html.escape(source_label)

        if lesson_num is None:
            return escaped_label

        lesson_link = self.store.get_lesson_link(course_title, lesson_num)
        if not self._is_safe_http_url(lesson_link):
            return escaped_label

        escaped_link = html.escape(lesson_link, quote=True)
        return (
            f'<a href="{escaped_link}" target="_blank" rel="noopener noreferrer">'
            f"{escaped_label}</a>"
        )

    def _is_safe_http_url(self, url: Optional[str]) -> bool:
        """Allow only http/https URLs for source links."""
        if not url:
            return False

        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


class CourseOutlineTool(Tool):
    """Tool for retrieving complete course outlines from metadata."""

    def __init__(self, vector_store: VectorStore):
        self.store = vector_store

    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for course outline retrieval."""
        return {
            "name": "get_course_outline",
            "description": (
                "Get complete course outline metadata including course title, "
                "course link, and all lessons"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "course_name": {
                        "type": "string",
                        "description": "Course title (partial matches work)",
                    }
                },
                "required": ["course_name"],
            },
        }

    def execute(self, course_name: str) -> str:
        """Return a normalized plain-text course outline for the given course."""
        outline = self.store.get_course_outline(course_name)
        if not outline:
            return f"No course outline found matching '{course_name}'."

        course_title = outline.get("title", course_name)
        course_link = outline.get("course_link")
        lessons = outline.get("lessons", [])
        course_link_line = "Course Link: N/A"

        if self._is_safe_http_url(course_link):
            escaped_course_link = html.escape(course_link, quote=True)
            course_link_line = (
                "Course Link: "
                f'<a href="{escaped_course_link}" target="_blank" '
                f'rel="noopener noreferrer">{escaped_course_link}</a>'
            )

        lines = [
            f"Course Title: {course_title}",
            "",
            course_link_line,
            "",
            "Lessons:",
        ]

        if not lessons:
            lines.append("No lessons found.")
        else:
            for lesson in lessons:
                lesson_number = lesson.get("lesson_number", "N/A")
                lesson_title = lesson.get("lesson_title", "Untitled")
                lesson_link = lesson.get("lesson_link")

                if self._is_safe_http_url(lesson_link):
                    escaped_link = html.escape(lesson_link, quote=True)
                    link_suffix = (
                        f' <a href="{escaped_link}" target="_blank" '
                        'rel="noopener noreferrer">(Link)</a>'
                    )
                else:
                    link_suffix = ""

                lines.append(f"- Lesson {lesson_number}: {lesson_title}{link_suffix}")

        return "\n".join(lines)

    def _is_safe_http_url(self, url: Optional[str]) -> bool:
        """Allow only http/https URLs for lesson links."""
        if not url:
            return False

        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


class ToolManager:
    """Manages available tools for the AI"""

    def __init__(self):
        self.tools = {}

    def register_tool(self, tool: Tool):
        """Register any tool that implements the Tool interface"""
        tool_def = tool.get_tool_definition()
        tool_name = tool_def.get("name")
        if not tool_name:
            raise ValueError("Tool must have a 'name' in its definition")
        self.tools[tool_name] = tool

    def get_tool_definitions(self) -> list:
        """Get all tool definitions for Anthropic tool calling"""
        return [tool.get_tool_definition() for tool in self.tools.values()]

    def execute_tool(self, tool_name: str, **kwargs) -> str:
        """Execute a tool by name with given parameters"""
        if tool_name not in self.tools:
            return f"Tool '{tool_name}' not found"

        return self.tools[tool_name].execute(**kwargs)

    def get_last_sources(self) -> list:
        """Get sources from the last search operation"""
        # Check all tools for last_sources attribute
        for tool in self.tools.values():
            if hasattr(tool, "last_sources") and tool.last_sources:
                return tool.last_sources
        return []

    def reset_sources(self):
        """Reset sources from all tools that track sources"""
        for tool in self.tools.values():
            if hasattr(tool, "last_sources"):
                tool.last_sources = []
