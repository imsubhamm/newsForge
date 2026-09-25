from __future__ import annotations

from typing import Any, Protocol

from app.config import Settings, get_settings


class AIProvider(Protocol):
    name: str

    def describe_scene(self, scene_id: str, image_paths: list[str], script_excerpt: str) -> dict[str, Any]:
        """Return structured scene understanding. Implemented in Milestone 6."""

    def build_timeline(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return a strict JSON editing plan. Implemented in Milestone 7."""

    def social_copy(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return grounded social captions. Implemented in Milestone 9."""


class MockAIProvider:
    name = "mock"

    def describe_scene(self, scene_id: str, image_paths: list[str], script_excerpt: str) -> dict[str, Any]:
        return {
            "scene_id": scene_id,
            "description": "Development fixture. Real vision analysis is disabled because MOCK_AI=true.",
            "subjects": ["news footage"],
            "actions": ["contextual b-roll"],
            "quality": 0.7,
            "news_value": 0.7,
            "frames_considered": [str(path) for path in image_paths],
            "grounded_in_script": bool(script_excerpt.strip()),
        }

    def build_timeline(self, payload: dict[str, Any]) -> dict[str, Any]:
        from app.services.semantic_planner import plan_from_payload

        return plan_from_payload(payload).model_dump()

    def social_copy(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Social copy is Milestone 9")


class OpenAICompatibleProvider:
    name = "openai"

    def __init__(self, settings: Settings):
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is missing. Use MOCK_AI=true for local development.")
        self.settings = settings

    def describe_scene(self, scene_id: str, image_paths: list[str], script_excerpt: str) -> dict[str, Any]:
        raise NotImplementedError("OpenAI vision analysis is Milestone 6")

    def build_timeline(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("OpenAI timeline generation is Milestone 7")

    def social_copy(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("OpenAI social copy is Milestone 9")


def get_ai_provider(settings: Settings | None = None) -> AIProvider:
    settings = settings or get_settings()
    if settings.mock_ai or settings.ai_provider == "mock":
        return MockAIProvider()
    if settings.ai_provider in {"openai", "openai-compatible"}:
        return OpenAICompatibleProvider(settings)
    raise RuntimeError(f"unknown AI provider: {settings.ai_provider}")
