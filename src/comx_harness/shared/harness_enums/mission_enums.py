from enum import StrEnum


class MissionExecutionProfile(StrEnum):
    CODEX_NATIVE = "codex-native"
    OMX_NATIVE = "omx-native"
    CODEX_THEN_OMX_REVIEW = "codex-then-omx-review"
