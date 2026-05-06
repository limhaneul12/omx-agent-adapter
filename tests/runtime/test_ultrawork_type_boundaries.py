def test_ultrawork_classifier_marker_sets_live_in_type_contracts() -> None:
    from omx_remote.adapter_types.type_contract.ultrawork_contract_type import (
        ULTRAWORK_NON_TERMINAL_OUTCOMES,
        ULTRAWORK_NON_TERMINAL_PHASES,
        ULTRAWORK_TERMINAL_OUTCOMES,
        ULTRAWORK_TERMINAL_PHASES,
    )
    from omx_remote.runtime.ultrawork.ultrawork_control import UltraworkStateClassifier

    assert ULTRAWORK_TERMINAL_PHASES
    assert ULTRAWORK_NON_TERMINAL_PHASES
    assert ULTRAWORK_TERMINAL_OUTCOMES
    assert ULTRAWORK_NON_TERMINAL_OUTCOMES
    assert "TERMINAL_PHASES" not in UltraworkStateClassifier.__dict__
    assert "NON_TERMINAL_PHASES" not in UltraworkStateClassifier.__dict__
    assert "TERMINAL_OUTCOMES" not in UltraworkStateClassifier.__dict__
    assert "NON_TERMINAL_OUTCOMES" not in UltraworkStateClassifier.__dict__
