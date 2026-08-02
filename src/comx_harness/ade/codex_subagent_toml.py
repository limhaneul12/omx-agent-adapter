from __future__ import annotations

import os
import stat
import tomllib
from contextlib import suppress
from pathlib import Path
from uuid import uuid4

import orjson
from comx_harness.schemas.codex_subagent_schemas import CodexSubagentSpec


def relative_agent_config_file(name: str) -> str:
    relative_path = f"agents/{name}.toml"
    return relative_path


def read_toml_file(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    parsed = parse_toml(path.read_text(encoding="utf-8"), path)
    return parsed


def parse_toml(text: str, path: Path) -> dict[str, object]:
    try:
        parsed = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"Invalid TOML at {path}: {error}") from error
    return parsed


def render_agent_file(agent: CodexSubagentSpec) -> str:
    text = "\n".join(
        (
            f"model = {_toml_string(agent.model)}",
            f"model_reasoning_effort = {_toml_string(agent.model_reasoning_effort)}",
            f"sandbox_mode = {_toml_string(agent.sandbox_mode)}",
            f"developer_instructions = {_toml_string(agent.developer_instructions)}",
            "",
        )
    )
    return text


def ensure_project_codex_directories(workspace_root: Path) -> None:
    if not _supports_directory_descriptors():
        raise OSError("Safe project-local Codex writes require directory descriptors")

    workspace_descriptor = _open_directory(workspace_root)
    try:
        codex_descriptor = _open_or_create_directory(workspace_descriptor, ".codex")
        try:
            agents_descriptor = _open_or_create_directory(
                codex_descriptor,
                "agents",
            )
            os.close(agents_descriptor)
        finally:
            os.close(codex_descriptor)
    finally:
        os.close(workspace_descriptor)


def atomic_write_project_file(
    workspace_root: Path,
    relative_path: Path,
    text: str,
) -> None:
    parts = relative_path.parts
    if relative_path.is_absolute() or not parts or parts[0] != ".codex":
        raise ValueError(f"Codex destination must be project-local: {relative_path}")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"Unsafe Codex destination: {relative_path}")
    if not _supports_directory_descriptors():
        raise OSError("Safe project-local Codex writes require directory descriptors")

    current_descriptor = _open_directory(workspace_root)
    try:
        for directory_name in parts[:-1]:
            next_descriptor = _open_directory_at(
                current_descriptor,
                directory_name,
            )
            os.close(current_descriptor)
            current_descriptor = next_descriptor
        _write_with_directory_descriptor(
            current_descriptor,
            parts[-1],
            text,
        )
    finally:
        os.close(current_descriptor)


def _supports_directory_descriptors() -> bool:
    required_functions = (os.open, os.stat, os.mkdir, os.unlink)
    supported = all(function in os.supports_dir_fd for function in required_functions)
    return supported


def _directory_open_flags() -> int:
    flags = os.O_RDONLY
    flags |= getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    return flags


def _open_directory(path: Path) -> int:
    descriptor = os.open(path, _directory_open_flags())
    return descriptor


def _open_directory_at(parent_descriptor: int, name: str) -> int:
    try:
        descriptor = os.open(
            name,
            _directory_open_flags(),
            dir_fd=parent_descriptor,
        )
    except OSError as error:
        raise ValueError(
            f"Refusing unsafe Codex directory component: {name}"
        ) from error
    return descriptor


def _open_or_create_directory(parent_descriptor: int, name: str) -> int:
    with suppress(FileExistsError):
        os.mkdir(name, mode=0o700, dir_fd=parent_descriptor)
    descriptor = _open_directory_at(parent_descriptor, name)
    return descriptor


def _write_with_directory_descriptor(
    directory_descriptor: int,
    file_name: str,
    text: str,
) -> None:
    try:
        current_stat = os.stat(
            file_name,
            dir_fd=directory_descriptor,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        existing_mode = 0o600
    else:
        if stat.S_ISLNK(current_stat.st_mode) or not stat.S_ISREG(current_stat.st_mode):
            raise ValueError(f"Refusing unsafe Codex file target: {file_name}")
        existing_mode = stat.S_IMODE(current_stat.st_mode)

    temporary_name = f".{file_name}.{uuid4().hex}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    file_descriptor = os.open(
        temporary_name,
        flags,
        existing_mode,
        dir_fd=directory_descriptor,
    )
    try:
        os.fchmod(file_descriptor, existing_mode)
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as stream:
            file_descriptor = -1
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(
            temporary_name,
            file_name,
            src_dir_fd=directory_descriptor,
            dst_dir_fd=directory_descriptor,
        )
    finally:
        if file_descriptor >= 0:
            os.close(file_descriptor)
        with suppress(FileNotFoundError):
            os.unlink(temporary_name, dir_fd=directory_descriptor)


def _toml_string(value: str) -> str:
    encoded = orjson.dumps(value).decode("utf-8")
    return encoded
