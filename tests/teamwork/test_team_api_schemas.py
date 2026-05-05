import pytest
from pydantic import ValidationError

from omx_remote.schemas.teamwork_schemas import (
    TeamApiBroadcastRequest,
    TeamApiClaimTaskRequest,
    TeamApiCleanupRequest,
    TeamApiCreateTaskRequest,
    TeamApiMailboxListRequest,
    TeamApiMailboxListSnapshot,
    TeamApiMailboxMarkDeliveredRequest,
    TeamApiMailboxMarkNotifiedRequest,
    TeamApiListTasksRequest,
    TeamApiListTasksSnapshot,
    TeamApiOrphanCleanupRequest,
    TeamApiReadEventsRequest,
    TeamApiReadEventsSnapshot,
    TeamApiReadMonitorSnapshotRequest,
    TeamApiReadMonitorSnapshot,
    TeamApiReadShutdownAckRequest,
    TeamApiReadTaskApprovalRequest,
    TeamApiReadTaskRequest,
    TeamApiReadWorkerStatusRequest,
    TeamApiReleaseTaskClaimRequest,
    TeamApiSendMessageRequest,
    TeamApiTransitionTaskStatusRequest,
    TeamApiUpdateTaskRequest,
    TeamApiWorkerInboxWriteRequest,
    TeamApiWorkerStatusSnapshot,
    TeamApiWriteShutdownRequest,
    TeamApiWriteTaskApprovalRequest,
    TeamOperatorDispatchInstructionRequest,
    TeamOperatorDispatchOutcome,
    TeamOperatorDispatchTaskRequest,
    TeamOperatorTaskApprovalRequest,
    TeamOperatorWorkerFollowUpOutcome,
    TeamOperatorWorkerRecheckRequest,
)


def test_team_api_list_tasks_request_accepts_required_team_name() -> None:
    result = TeamApiListTasksRequest.model_validate({"team_name": "alpha"})

    assert result.team_name == "alpha"


def test_team_api_list_tasks_request_rejects_empty_team_name() -> None:
    with pytest.raises(ValidationError):
        TeamApiListTasksRequest.model_validate({"team_name": ""})


def test_team_api_list_tasks_snapshot_accepts_empty_task_list() -> None:
    result = TeamApiListTasksSnapshot.model_validate(
        {"count": 0, "tasks": []}
    )

    assert result.count == 0
    assert result.tasks == []


def test_team_api_list_tasks_snapshot_rejects_unexpected_extra_fields() -> None:
    with pytest.raises(ValidationError):
        TeamApiListTasksSnapshot.model_validate(
            {"count": 0, "tasks": [], "unexpected": True}
        )


def test_team_api_list_tasks_snapshot_accepts_normalized_live_task_shape() -> None:
    result = TeamApiListTasksSnapshot.model_validate(
        {
            "count": 1,
            "tasks": [
                {
                    "id": "1",
                    "subject": "Team surface closure",
                    "status": "in_progress",
                    "owner": "worker-1",
                }
            ],
        }
    )

    assert result.tasks[0].subject == "Team surface closure"
    assert result.tasks[0].owner == "worker-1"


def test_team_api_read_events_request_accepts_required_team_name() -> None:
    result = TeamApiReadEventsRequest.model_validate({"team_name": "alpha"})

    assert result.team_name == "alpha"


def test_team_api_read_monitor_snapshot_request_accepts_required_team_name() -> None:
    result = TeamApiReadMonitorSnapshotRequest.model_validate({"team_name": "alpha"})

    assert result.team_name == "alpha"


def test_team_api_read_monitor_snapshot_request_rejects_empty_team_name() -> None:
    with pytest.raises(ValidationError):
        TeamApiReadMonitorSnapshotRequest.model_validate({"team_name": ""})


def test_team_api_read_monitor_snapshot_accepts_null_snapshot() -> None:
    result = TeamApiReadMonitorSnapshot.model_validate({"snapshot": None})

    assert result.snapshot is None


def test_team_api_read_monitor_snapshot_rejects_unexpected_extra_fields() -> None:
    with pytest.raises(ValidationError):
        TeamApiReadMonitorSnapshot.model_validate(
            {"snapshot": None, "unexpected": True}
        )


def test_team_api_read_events_request_rejects_empty_team_name() -> None:
    with pytest.raises(ValidationError):
        TeamApiReadEventsRequest.model_validate({"team_name": ""})


def test_team_api_send_message_request_accepts_required_fields() -> None:
    result = TeamApiSendMessageRequest.model_validate(
        {
            "team_name": "alpha",
            "from_worker": "worker-1",
            "to_worker": "worker-2",
            "body": "ACK",
        }
    )

    assert result.team_name == "alpha"
    assert result.from_worker == "worker-1"
    assert result.to_worker == "worker-2"
    assert result.body == "ACK"


def test_team_api_send_message_request_rejects_empty_to_worker() -> None:
    with pytest.raises(ValidationError):
        TeamApiSendMessageRequest.model_validate(
            {
                "team_name": "alpha",
                "from_worker": "worker-1",
                "to_worker": "",
                "body": "ACK",
            }
        )


def test_team_api_worker_inbox_write_request_accepts_required_fields() -> None:
    result = TeamApiWorkerInboxWriteRequest.model_validate(
        {
            "team_name": "alpha",
            "worker": "worker-1",
            "content": "# Inbox update\nProceed.",
        }
    )

    assert result.team_name == "alpha"
    assert result.worker == "worker-1"
    assert result.content == "# Inbox update\nProceed."


def test_team_api_worker_inbox_write_request_rejects_empty_content() -> None:
    with pytest.raises(ValidationError):
        TeamApiWorkerInboxWriteRequest.model_validate(
            {"team_name": "alpha", "worker": "worker-1", "content": ""}
        )


def test_team_api_broadcast_request_accepts_required_fields() -> None:
    result = TeamApiBroadcastRequest.model_validate(
        {
            "team_name": "alpha",
            "from_worker": "worker-1",
            "body": "ACK",
        }
    )

    assert result.team_name == "alpha"
    assert result.from_worker == "worker-1"
    assert result.body == "ACK"


def test_team_api_broadcast_request_rejects_empty_body() -> None:
    with pytest.raises(ValidationError):
        TeamApiBroadcastRequest.model_validate(
            {"team_name": "alpha", "from_worker": "worker-1", "body": ""}
        )


def test_team_api_create_task_request_accepts_required_fields() -> None:
    result = TeamApiCreateTaskRequest.model_validate(
        {
            "team_name": "alpha",
            "subject": "Demo task",
            "description": "Created through CLI interop",
        }
    )

    assert result.team_name == "alpha"
    assert result.subject == "Demo task"
    assert result.description == "Created through CLI interop"
    assert result.blocked_by == []


def test_team_api_create_task_request_rejects_empty_subject() -> None:
    with pytest.raises(ValidationError):
        TeamApiCreateTaskRequest.model_validate(
            {
                "team_name": "alpha",
                "subject": "",
                "description": "Created through CLI interop",
            }
        )


def test_team_api_read_task_request_accepts_required_fields() -> None:
    result = TeamApiReadTaskRequest.model_validate(
        {"team_name": "alpha", "task_id": "1"}
    )

    assert result.team_name == "alpha"
    assert result.task_id == "1"


def test_team_api_read_task_request_rejects_empty_task_id() -> None:
    with pytest.raises(ValidationError):
        TeamApiReadTaskRequest.model_validate({"team_name": "alpha", "task_id": ""})


def test_team_api_transition_task_status_request_accepts_required_fields() -> None:
    result = TeamApiTransitionTaskStatusRequest.model_validate(
        {
            "team_name": "alpha",
            "task_id": "1",
            "from_status": "in_progress",
            "to_status": "completed",
            "claim_token": "claim-token",
        }
    )

    assert result.team_name == "alpha"
    assert result.task_id == "1"
    assert result.from_status == "in_progress"
    assert result.to_status == "completed"
    assert result.claim_token == "claim-token"


def test_team_api_transition_task_status_request_rejects_empty_claim_token() -> None:
    with pytest.raises(ValidationError):
        TeamApiTransitionTaskStatusRequest.model_validate(
            {
                "team_name": "alpha",
                "task_id": "1",
                "from_status": "in_progress",
                "to_status": "completed",
                "claim_token": "",
            }
        )



def test_team_api_update_task_request_accepts_optional_metadata_fields() -> None:
    result = TeamApiUpdateTaskRequest.model_validate(
        {
            "team_name": "alpha",
            "task_id": "1",
            "subject": "Refined task",
            "blocked_by": [],
            "requires_code_change": False,
        }
    )

    assert result.team_name == "alpha"
    assert result.task_id == "1"
    assert result.subject == "Refined task"
    assert result.blocked_by == []
    assert result.requires_code_change is False



def test_team_api_update_task_request_rejects_empty_task_id() -> None:
    with pytest.raises(ValidationError):
        TeamApiUpdateTaskRequest.model_validate({"team_name": "alpha", "task_id": ""})



def test_team_api_claim_task_request_accepts_optional_expected_version() -> None:
    result = TeamApiClaimTaskRequest.model_validate(
        {
            "team_name": "alpha",
            "task_id": "1",
            "worker": "worker-1",
            "expected_version": 3,
        }
    )

    assert result.team_name == "alpha"
    assert result.task_id == "1"
    assert result.worker == "worker-1"
    assert result.expected_version == 3



def test_team_api_claim_task_request_rejects_negative_expected_version() -> None:
    with pytest.raises(ValidationError):
        TeamApiClaimTaskRequest.model_validate(
            {
                "team_name": "alpha",
                "task_id": "1",
                "worker": "worker-1",
                "expected_version": -1,
            }
        )



def test_team_api_release_task_claim_request_accepts_required_fields() -> None:
    result = TeamApiReleaseTaskClaimRequest.model_validate(
        {
            "team_name": "alpha",
            "task_id": "1",
            "claim_token": "claim-token",
            "worker": "worker-1",
        }
    )

    assert result.team_name == "alpha"
    assert result.task_id == "1"
    assert result.claim_token == "claim-token"
    assert result.worker == "worker-1"



def test_team_api_release_task_claim_request_rejects_empty_worker() -> None:
    with pytest.raises(ValidationError):
        TeamApiReleaseTaskClaimRequest.model_validate(
            {
                "team_name": "alpha",
                "task_id": "1",
                "claim_token": "claim-token",
                "worker": "",
            }
        )



def test_team_api_read_task_approval_request_accepts_required_fields() -> None:
    result = TeamApiReadTaskApprovalRequest.model_validate(
        {"team_name": "alpha", "task_id": "1"}
    )

    assert result.team_name == "alpha"
    assert result.task_id == "1"



def test_team_api_read_task_approval_request_rejects_empty_task_id() -> None:
    with pytest.raises(ValidationError):
        TeamApiReadTaskApprovalRequest.model_validate({"team_name": "alpha", "task_id": ""})



def test_team_api_write_task_approval_request_accepts_required_fields() -> None:
    result = TeamApiWriteTaskApprovalRequest.model_validate(
        {
            "team_name": "alpha",
            "task_id": "1",
            "status": "approved",
            "reviewer": "leader-fixed",
            "decision_reason": "approved in demo",
            "required": True,
        }
    )

    assert result.team_name == "alpha"
    assert result.task_id == "1"
    assert result.status == "approved"
    assert result.reviewer == "leader-fixed"
    assert result.decision_reason == "approved in demo"
    assert result.required is True



def test_team_api_write_task_approval_request_rejects_empty_decision_reason() -> None:
    with pytest.raises(ValidationError):
        TeamApiWriteTaskApprovalRequest.model_validate(
            {
                "team_name": "alpha",
                "task_id": "1",
                "status": "approved",
                "reviewer": "leader-fixed",
                "decision_reason": "",
            }
        )



def test_team_api_mailbox_mark_delivered_request_accepts_required_fields() -> None:
    result = TeamApiMailboxMarkDeliveredRequest.model_validate(
        {
            "team_name": "alpha",
            "worker": "worker-1",
            "message_id": "message-1",
        }
    )

    assert result.team_name == "alpha"
    assert result.worker == "worker-1"
    assert result.message_id == "message-1"



def test_team_api_mailbox_mark_delivered_request_rejects_empty_message_id() -> None:
    with pytest.raises(ValidationError):
        TeamApiMailboxMarkDeliveredRequest.model_validate(
            {
                "team_name": "alpha",
                "worker": "worker-1",
                "message_id": "",
            }
        )



def test_team_api_mailbox_mark_notified_request_accepts_required_fields() -> None:
    result = TeamApiMailboxMarkNotifiedRequest.model_validate(
        {
            "team_name": "alpha",
            "worker": "worker-1",
            "message_id": "message-1",
        }
    )

    assert result.team_name == "alpha"
    assert result.worker == "worker-1"
    assert result.message_id == "message-1"



def test_team_api_mailbox_mark_notified_request_rejects_empty_worker() -> None:
    with pytest.raises(ValidationError):
        TeamApiMailboxMarkNotifiedRequest.model_validate(
            {
                "team_name": "alpha",
                "worker": "",
                "message_id": "message-1",
            }
        )



def test_team_api_write_shutdown_request_accepts_required_fields() -> None:
    result = TeamApiWriteShutdownRequest.model_validate(
        {
            "team_name": "alpha",
            "worker": "worker-1",
            "requested_by": "leader-fixed",
        }
    )

    assert result.team_name == "alpha"
    assert result.worker == "worker-1"
    assert result.requested_by == "leader-fixed"



def test_team_api_write_shutdown_request_rejects_empty_requested_by() -> None:
    with pytest.raises(ValidationError):
        TeamApiWriteShutdownRequest.model_validate(
            {
                "team_name": "alpha",
                "worker": "worker-1",
                "requested_by": "",
            }
        )



def test_team_api_read_shutdown_ack_request_accepts_optional_min_updated_at() -> None:
    result = TeamApiReadShutdownAckRequest.model_validate(
        {
            "team_name": "alpha",
            "worker": "worker-1",
            "min_updated_at": "2026-05-05T00:00:00Z",
        }
    )

    assert result.team_name == "alpha"
    assert result.worker == "worker-1"
    assert result.min_updated_at == "2026-05-05T00:00:00Z"



def test_team_api_read_shutdown_ack_request_rejects_empty_worker() -> None:
    with pytest.raises(ValidationError):
        TeamApiReadShutdownAckRequest.model_validate(
            {
                "team_name": "alpha",
                "worker": "",
            }
        )



def test_team_api_cleanup_request_accepts_optional_flags() -> None:
    result = TeamApiCleanupRequest.model_validate(
        {
            "team_name": "alpha",
            "force": True,
            "confirm_issues": True,
        }
    )

    assert result.team_name == "alpha"
    assert result.force is True
    assert result.confirm_issues is True



def test_team_api_cleanup_request_rejects_empty_team_name() -> None:
    with pytest.raises(ValidationError):
        TeamApiCleanupRequest.model_validate({"team_name": ""})



def test_team_api_orphan_cleanup_request_accepts_required_team_name() -> None:
    result = TeamApiOrphanCleanupRequest.model_validate({"team_name": "alpha"})

    assert result.team_name == "alpha"



def test_team_api_orphan_cleanup_request_rejects_empty_team_name() -> None:
    with pytest.raises(ValidationError):
        TeamApiOrphanCleanupRequest.model_validate({"team_name": ""})



def test_team_api_mailbox_list_request_accepts_required_fields() -> None:
    result = TeamApiMailboxListRequest.model_validate(
        {"team_name": "alpha", "worker": "worker-1"}
    )

    assert result.team_name == "alpha"
    assert result.worker == "worker-1"


def test_team_api_mailbox_list_request_rejects_empty_worker() -> None:
    with pytest.raises(ValidationError):
        TeamApiMailboxListRequest.model_validate(
            {"team_name": "alpha", "worker": ""}
        )


def test_team_api_read_worker_status_request_accepts_required_fields() -> None:
    result = TeamApiReadWorkerStatusRequest.model_validate(
        {"team_name": "alpha", "worker": "worker-1"}
    )

    assert result.team_name == "alpha"
    assert result.worker == "worker-1"


def test_team_api_worker_status_snapshot_accepts_live_shape() -> None:
    result = TeamApiWorkerStatusSnapshot.model_validate(
        {
            "worker": "worker-1",
            "state": "unknown",
            "updated_at": "1970-01-01T00:00:00.000Z",
        }
    )

    assert result.worker == "worker-1"
    assert result.state == "unknown"


def test_team_api_mailbox_list_snapshot_accepts_empty_message_list() -> None:
    result = TeamApiMailboxListSnapshot.model_validate(
        {"worker": "worker-1", "count": 0, "messages": []}
    )

    assert result.worker == "worker-1"
    assert result.count == 0
    assert result.messages == []


def test_team_api_mailbox_list_snapshot_rejects_unexpected_extra_fields() -> None:
    with pytest.raises(ValidationError):
        TeamApiMailboxListSnapshot.model_validate(
            {
                "worker": "worker-1",
                "count": 0,
                "messages": [],
                "unexpected": True,
            }
        )


def test_team_api_mailbox_list_snapshot_accepts_normalized_live_message_shape() -> None:
    result = TeamApiMailboxListSnapshot.model_validate(
        {
            "worker": "worker-1",
            "count": 1,
            "messages": [
                {
                    "id": "message-1",
                    "subject": "follow-up",
                    "body": "please re-run tests",
                    "delivered": False,
                }
            ],
        }
    )

    assert result.messages[0].id == "message-1"
    assert result.messages[0].delivered is False


def test_team_api_read_events_snapshot_accepts_empty_event_list() -> None:
    result = TeamApiReadEventsSnapshot.model_validate(
        {"count": 0, "cursor": "", "events": []}
    )

    assert result.count == 0
    assert result.cursor == ""
    assert result.events == []


def test_team_api_read_events_snapshot_rejects_unexpected_extra_fields() -> None:
    with pytest.raises(ValidationError):
        TeamApiReadEventsSnapshot.model_validate(
            {"count": 0, "cursor": "", "events": [], "unexpected": True}
        )


def test_team_api_read_events_snapshot_accepts_normalized_live_event_shape() -> None:
    result = TeamApiReadEventsSnapshot.model_validate(
        {
            "count": 1,
            "cursor": "cursor-1",
            "events": [
                {
                    "type": "message_received",
                    "worker": "leader-fixed",
                    "message_id": "message-1",
                }
            ],
        }
    )

    assert result.events[0].type == "message_received"
    assert result.events[0].message_id == "message-1"



def test_team_operator_dispatch_instruction_request_accepts_optional_worker_target() -> None:
    result = TeamOperatorDispatchInstructionRequest.model_validate(
        {
            "team_name": "alpha",
            "from_worker": "leader-fixed",
            "body": "Please re-run checks.",
            "to_worker": "worker-1",
            "durable_delivery": True,
        }
    )

    assert result.team_name == "alpha"
    assert result.to_worker == "worker-1"
    assert result.durable_delivery is True



def test_team_operator_dispatch_task_request_rejects_empty_subject() -> None:
    with pytest.raises(ValidationError):
        TeamOperatorDispatchTaskRequest.model_validate(
            {
                "team_name": "alpha",
                "subject": "",
                "description": "ship slice",
            }
        )



def test_team_operator_task_approval_request_accepts_required_fields() -> None:
    result = TeamOperatorTaskApprovalRequest.model_validate(
        {
            "team_name": "alpha",
            "task_id": "1",
            "status": "approved",
            "reviewer": "leader-fixed",
            "decision_reason": "looks good",
        }
    )

    assert result.task_id == "1"
    assert result.status == "approved"



def test_team_operator_worker_recheck_request_rejects_empty_body() -> None:
    with pytest.raises(ValidationError):
        TeamOperatorWorkerRecheckRequest.model_validate(
            {
                "team_name": "alpha",
                "from_worker": "leader-fixed",
                "worker": "worker-1",
                "body": "",
            }
        )



def test_team_operator_dispatch_outcome_accepts_command_result() -> None:
    result = TeamOperatorDispatchOutcome.model_validate(
        {
            "selected_operation": "write-worker-inbox",
            "outcome": "accepted_but_unverified",
            "needs_follow_up": True,
            "reason": "inbox writes can report success without proving mailbox state",
            "command_result": {
                "exit_code": 0,
                "stdout": "{}",
                "stderr": "",
            },
        }
    )

    assert result.selected_operation == "write-worker-inbox"
    assert result.command_result.exit_code == 0



def test_team_operator_worker_follow_up_outcome_accepts_nested_dispatch_result() -> None:
    result = TeamOperatorWorkerFollowUpOutcome.model_validate(
        {
            "worker_state": "unknown",
            "selected_delivery_mode": "durable_inbox",
            "dispatch_result": {
                "selected_operation": "write-worker-inbox",
                "outcome": "accepted_but_unverified",
                "needs_follow_up": True,
                "reason": "worker state unknown so durable inbox chosen",
                "command_result": {
                    "exit_code": 0,
                    "stdout": "{}",
                    "stderr": "",
                },
            },
        }
    )

    assert result.worker_state == "unknown"
    assert result.dispatch_result.selected_operation == "write-worker-inbox"
