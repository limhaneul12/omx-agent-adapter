from omx_remote.schemas.route_policy_schemas import (
    RouteTaskSize,
    RouteTaskType,
    TaskClassification,
)

_REVIEW_MARKERS: tuple[str, ...] = ("review", "diff", "pr")
_RESEARCH_MARKERS: tuple[str, ...] = ("research", "investigate", "docs")
_PERFORMANCE_MARKERS: tuple[str, ...] = ("performance", "benchmark", "optimize")
_REFACTOR_MARKERS: tuple[str, ...] = ("refactor", "cleanup", "deslop")
_VERIFY_MARKERS: tuple[str, ...] = ("verify", "test", "qa", "lint", "typecheck")
_DOC_MARKERS: tuple[str, ...] = ("document", "docs", "readme")
_ROADMAP_MARKERS: tuple[str, ...] = ("roadmap", "multi-goal", "ultragoal", "brief")
_PARALLEL_MARKERS: tuple[str, ...] = ("parallel", "workers", "subagents", "split")


def _contains_any(normalized_task: str, markers: tuple[str, ...]) -> bool:
    """Return whether a normalized task contains any marker.

    Args:
        normalized_task [str]: Lowercase task text.
        markers [tuple[str, ...]]: Markers to search for.

    Returns:
        bool: ``True`` when at least one marker is present.
    """
    contains_marker: bool = any(marker in normalized_task for marker in markers)
    return contains_marker


def _classify_task_type(normalized_task: str) -> RouteTaskType:
    """Classify the dominant task type from text markers.

    Args:
        normalized_task [str]: Lowercase task text.

    Returns:
        RouteTaskType: Deterministic task type signal.
    """
    if _contains_any(normalized_task, _REVIEW_MARKERS):
        task_type: RouteTaskType = RouteTaskType.REVIEW
        return task_type
    if _contains_any(normalized_task, _RESEARCH_MARKERS):
        task_type = RouteTaskType.RESEARCH
        return task_type
    if _contains_any(normalized_task, _PERFORMANCE_MARKERS):
        task_type = RouteTaskType.PERFORMANCE
        return task_type
    if _contains_any(normalized_task, _REFACTOR_MARKERS):
        task_type = RouteTaskType.REFACTOR
        return task_type
    if _contains_any(normalized_task, _VERIFY_MARKERS):
        task_type = RouteTaskType.VERIFICATION
        return task_type
    if _contains_any(normalized_task, _DOC_MARKERS):
        task_type = RouteTaskType.DOCUMENTATION
        return task_type

    task_type = RouteTaskType.IMPLEMENTATION
    return task_type


def _classify_task_size(normalized_task: str) -> RouteTaskSize:
    """Classify the task size from text markers.

    Args:
        normalized_task [str]: Lowercase task text.

    Returns:
        RouteTaskSize: Deterministic size signal.
    """
    if _contains_any(normalized_task, _ROADMAP_MARKERS):
        task_size: RouteTaskSize = RouteTaskSize.ROADMAP
        return task_size
    if _contains_any(normalized_task, _PARALLEL_MARKERS):
        task_size = RouteTaskSize.MEDIUM
        return task_size
    if "current diff" in normalized_task:
        task_size = RouteTaskSize.SMALL
        return task_size

    task_size = RouteTaskSize.MEDIUM
    return task_size


def _collect_signals(normalized_task: str) -> tuple[str, ...]:
    """Collect named task signals from text markers.

    Args:
        normalized_task [str]: Lowercase task text.

    Returns:
        tuple[str, ...]: Stable signal names for route policy.
    """
    signals: list[str] = []
    if "current diff" in normalized_task or "diff" in normalized_task:
        signals.append("current_diff")
    if _contains_any(normalized_task, _ROADMAP_MARKERS):
        signals.append("roadmap")
    if _contains_any(normalized_task, _PARALLEL_MARKERS):
        signals.append("parallel_workers")
    if "performance" in normalized_task or "benchmark" in normalized_task:
        signals.append("performance")
    if "research" in normalized_task or "investigate" in normalized_task:
        signals.append("research")

    collected_signals: tuple[str, ...] = tuple(signals)
    return collected_signals


def classify_task_signals(task: str) -> TaskClassification:
    """Classify task text into stable route-policy signals.

    Args:
        task [str]: Human or agent task text.

    Returns:
        TaskClassification: Typed task classification.
    """
    normalized_task: str = task.strip().lower()
    signals: tuple[str, ...] = _collect_signals(normalized_task)
    classification = TaskClassification(
        task=task,
        size=_classify_task_size(normalized_task),
        task_type=_classify_task_type(normalized_task),
        needs_parallelism="parallel_workers" in signals,
        needs_durable_state="roadmap" in signals,
        signals=signals,
    )
    return classification
