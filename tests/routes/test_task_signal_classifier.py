from omx_remote.runtime.routes.task_signal_classifier import classify_task_signals
from omx_remote.schemas.routes.route_policy_schemas import RouteTaskSize, RouteTaskType


def test_classifier_detects_review_current_diff_as_small_review() -> None:
    classification = classify_task_signals("review current diff")

    assert classification.size == RouteTaskSize.SMALL
    assert classification.task_type == RouteTaskType.REVIEW
    assert "current_diff" in classification.signals


def test_classifier_detects_roadmap_as_durable_multi_goal_work() -> None:
    classification = classify_task_signals(
        "execute this roadmap with multiple goals from the brief"
    )

    assert classification.size == RouteTaskSize.ROADMAP
    assert classification.task_type == RouteTaskType.IMPLEMENTATION
    assert classification.needs_durable_state is True
    assert "roadmap" in classification.signals


def test_classifier_detects_parallel_refactor_worker_signal() -> None:
    classification = classify_task_signals(
        "split this refactor across workers by file owner"
    )

    assert classification.task_type == RouteTaskType.REFACTOR
    assert classification.needs_parallelism is True
    assert "parallel_workers" in classification.signals
