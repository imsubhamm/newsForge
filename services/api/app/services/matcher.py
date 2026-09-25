from __future__ import annotations

from app.schemas import NarrationSegment, SceneCandidate, VisualScene
from app.services.alignment import normalize_token


def score_scene(
    narration: NarrationSegment,
    scene: VisualScene,
    usage: dict[str, int],
    recent: list[str],
    used_ranges: list[tuple[str, float, float]],
) -> float:
    semantic = _semantic_score(narration, scene)
    quality = 0.08 * scene.quality_score + 0.08 * scene.visual_interest_score + 0.04 * scene.stability_score
    penalty = 0.22 * usage.get(scene.scene_id, 0)
    if scene.scene_id in recent[-2:]:
        penalty += 0.18
    penalty += 0.25 * _overlap_penalty(scene, used_ranges)
    continuity = 0.0
    if recent:
        prev = recent[-1]
        if scene.scene_id.startswith(prev.rsplit("_scene_", 1)[0]) and scene.source_start >= 0:
            continuity = 0.06
    return max(0.0, min(1.0, semantic + quality + continuity - penalty))


def rank_candidates(
    narration: NarrationSegment,
    scenes: list[VisualScene],
    usage: dict[str, int],
    recent: list[str],
    used_ranges: list[tuple[str, float, float]],
) -> list[SceneCandidate]:
    ranked: list[SceneCandidate] = []
    for scene in scenes:
        score = score_scene(narration, scene, usage, recent, used_ranges)
        ranked.append(
            SceneCandidate(
                scene_id=scene.scene_id,
                source_file=scene.source_file,
                source_start=scene.source_start,
                source_end=scene.source_end,
                score=round(score, 3),
                reason=_reason(narration, scene, score),
            )
        )
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked


def _semantic_score(narration: NarrationSegment, scene: VisualScene) -> float:
    needles = _bag(
        [narration.text, *narration.entities, *narration.visual_requirements, *narration.actions, narration.type]
    )
    hay = _bag([scene.description, *scene.subjects, *scene.actions, *scene.environment])
    if not needles:
        return 0.2
    if not hay:
        return 0.12
    overlap = needles & hay
    if not overlap:
        return 0.1
    return min(0.92, 0.28 + 0.22 * len(overlap))


def _bag(parts: list[str]) -> set[str]:
    tokens: set[str] = set()
    for part in parts:
        for token in str(part).replace(",", " ").split():
            key = normalize_token(token)
            if len(key) >= 3:
                tokens.add(key)
    return tokens


def _overlap_penalty(scene: VisualScene, used_ranges: list[tuple[str, float, float]]) -> float:
    penalty = 0.0
    for source, start, end in used_ranges:
        if source != scene.source_file:
            continue
        latest_start = max(start, scene.source_start)
        earliest_end = min(end, scene.source_end)
        overlap = earliest_end - latest_start
        if overlap > 0.2:
            penalty += min(1.0, overlap / max(scene.duration, 0.4))
    return penalty


def _reason(narration: NarrationSegment, scene: VisualScene, score: float) -> str:
    if score >= 0.7:
        return f"Strong match for {narration.type}: {scene.scene_id}"
    if score >= 0.45:
        return f"Usable visual for {narration.id}"
    return f"Weak match; {scene.scene_id} is a fallback, not invented evidence"
