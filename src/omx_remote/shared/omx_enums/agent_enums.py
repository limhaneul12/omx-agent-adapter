from enum import StrEnum


class AgentProvider(StrEnum):
    """Supported subagent configuration providers."""

    CODEX = "codex"


class AgentEffort(StrEnum):
    """Supported reasoning effort labels for configured subagents."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"


class CodexAgentMaterializationTarget(StrEnum):
    """Supported Codex-native agent materialization targets."""

    PROJECT = "project"
    GLOBAL = "global"
