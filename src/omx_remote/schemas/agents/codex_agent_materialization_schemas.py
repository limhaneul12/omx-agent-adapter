from pydantic import Field

from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel


class CodexAgentCapabilitySnapshot(StrictSchemaModel):
    """Represents verified Codex native-agent materialization capability."""

    codex_home: NonEmptyString
    codex_version: NonEmptyString | None = None
    native_agent_toml_supported: bool
    supported_materialization_targets: tuple[NonEmptyString, ...] = ()
    warnings: tuple[NonEmptyString, ...] = ()


class CodexAgentMaterializationFile(StrictSchemaModel):
    """Represents one planned Codex-native generated agent file."""

    agent_id: NonEmptyString
    target_path: NonEmptyString
    content_sha256: NonEmptyString
    content: NonEmptyString


class CodexAgentMaterializationPlan(StrictSchemaModel):
    """Represents the dry-run plan for Codex agent materialization."""

    supported: bool
    capability: CodexAgentCapabilitySnapshot
    source_config_path: NonEmptyString
    files: tuple[CodexAgentMaterializationFile, ...] = ()
    warnings: tuple[NonEmptyString, ...] = ()


class CodexAgentMaterializationApplyResult(StrictSchemaModel):
    """Represents Codex agent materialization apply output."""

    dry_run: bool
    plan: CodexAgentMaterializationPlan
    written_files: tuple[NonEmptyString, ...] = ()
    warnings: tuple[NonEmptyString, ...] = ()


class CodexAgentMaterializationFileStatus(StrictSchemaModel):
    """Represents generated-file status for one Codex agent."""

    agent_id: NonEmptyString
    target_path: NonEmptyString
    exists: bool
    matches: bool
    expected_sha256: NonEmptyString
    actual_sha256: NonEmptyString | None = None


class CodexAgentMaterializationStatus(StrictSchemaModel):
    """Represents status of generated Codex-native agent artifacts."""

    up_to_date: bool
    supported: bool
    files: tuple[CodexAgentMaterializationFileStatus, ...] = ()
    warning_count: int = Field(ge=0)
    warnings: tuple[NonEmptyString, ...] = ()
