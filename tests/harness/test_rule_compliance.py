from __future__ import annotations

import ast
from pathlib import Path

SOURCE_ROOT = Path(__file__).parents[2] / "src" / "comx_harness"
MAX_RUNTIME_LINES = 430
PUBLIC_OPERATIONS = {
    "capabilities",
    "plan",
    "run",
    "handoff",
    "status",
    "events",
    "cancel",
    "resume",
    "artifacts",
}
FACADE_EXCEPTIONS = {
    "controller_surface.py:HarnessTools",
    "application/harness_service.py:HarnessService",
}
OBSOLETE_OMNIBUS_MODULES = {
    "contracts.py",
    "errors.py",
    "providers.py",
    "service.py",
    "store.py",
}


def _python_files() -> tuple[Path, ...]:
    files = tuple(sorted(SOURCE_ROOT.rglob("*.py")))
    return files


def _base_name(base: ast.expr) -> str | None:
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    if isinstance(base, ast.Subscript):
        return _base_name(base.value)
    return None


def _public_methods(class_node: ast.ClassDef) -> set[str]:
    methods = {
        node.name
        for node in class_node.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }
    return methods


def test_obsolete_omnibus_modules_are_removed() -> None:
    existing = {path.name for path in SOURCE_ROOT.iterdir() if path.is_file()}
    remaining = existing & OBSOLETE_OMNIBUS_MODULES
    assert remaining == set()


def test_production_json_uses_orjson_only() -> None:
    violations: list[str] = []
    for path in _python_files():
        relative_path = path.relative_to(SOURCE_ROOT)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(
                alias.name == "json" for alias in node.names
            ):
                violations.append(f"{relative_path}:{node.lineno}")
            if isinstance(node, ast.ImportFrom) and node.module == "json":
                violations.append(f"{relative_path}:{node.lineno}")
    assert violations == []


def test_contract_enums_and_exceptions_use_concept_owned_locations() -> None:
    violations: list[str] = []
    for path in _python_files():
        relative_path = path.relative_to(SOURCE_ROOT)
        parts = relative_path.parts
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            base_names = {_base_name(base) for base in node.bases}
            location = f"{relative_path}:{node.lineno}:{node.name}"
            if (
                base_names & {"BaseModel", "RootModel", "StrictModel"}
                and "schemas" not in parts
            ):
                violations.append(f"schema outside schemas/: {location}")
            if "StrEnum" in base_names:
                expected_prefix = ("shared", "harness_enums")
                if parts[:2] != expected_prefix:
                    violations.append(f"enum outside shared/harness_enums/: {location}")
            if node.name.endswith("Error"):
                expected_prefix = ("shared", "exceptions")
                if parts[:2] != expected_prefix:
                    violations.append(
                        f"exception outside shared/exceptions/: {location}"
                    )
    assert violations == []


def test_runtime_modules_and_classes_remain_cohesive() -> None:
    violations: list[str] = []
    for path in _python_files():
        relative_path = path.relative_to(SOURCE_ROOT)
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        if line_count > MAX_RUNTIME_LINES:
            violations.append(
                f"module exceeds {MAX_RUNTIME_LINES} lines: {relative_path}={line_count}"
            )
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            public_methods = _public_methods(node)
            facade_key = f"{relative_path}:{node.name}"
            if facade_key in FACADE_EXCEPTIONS:
                if public_methods != PUBLIC_OPERATIONS:
                    violations.append(
                        f"facade operation drift: {facade_key}={sorted(public_methods)}"
                    )
                continue
            if len(public_methods) > 6:
                violations.append(
                    f"class exceeds 6 public methods: {facade_key}={sorted(public_methods)}"
                )
    assert violations == []
