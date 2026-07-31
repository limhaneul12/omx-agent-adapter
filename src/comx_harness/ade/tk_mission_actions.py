from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from comx_harness.ade.tk_app import AdeTkApplication


def plan_mission(app: AdeTkApplication) -> None:
    try:
        request = app.ui.mission.request(str(app._require_controller().workspace))
        plan = app._missions.plan(request)
    except Exception as error:
        app._show_error("Mission plan failed", error)
        return
    app._planned_mission = request
    app.ui.mission.show_plan(plan.model_dump_json(indent=2))
    app.ui.status.set(f"Mission {request.mission_id} is ready for review.")


def execute_mission(app: AdeTkApplication) -> None:
    try:
        request = app._planned_mission or app.ui.mission.request(
            str(app._require_controller().workspace)
        )
        operation = app._missions.execute(request)
    except Exception as error:
        app._show_error("Mission launch failed", error)
        return
    app._planned_mission = None
    app.ui.status.set(
        f"Mission {request.mission_id} started as detached Strategy "
        f"{operation.strategy_id}."
    )
    app.ui.main_tabs.select(0)
    app._refresh_all()
