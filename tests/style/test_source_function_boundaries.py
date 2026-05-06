import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "src" / "omx_remote"


def _source_functions() -> list[tuple[Path, ast.FunctionDef | ast.AsyncFunctionDef]]:
    functions: list[tuple[Path, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    for source_path in sorted(SOURCE_ROOT.rglob("*.py")):
        module_tree = ast.parse(source_path.read_text(), filename=str(source_path))
        for node in ast.walk(module_tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                functions.append((source_path, node))
    return functions


def _meaningful_parameters(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    parameter_names: list[str] = []
    positional_args = [*node.args.posonlyargs, *node.args.args]
    for parameter in [*positional_args, *node.args.kwonlyargs]:
        if parameter.arg in {"self", "cls"}:
            continue
        parameter_names.append(parameter.arg)
    if node.args.vararg is not None:
        parameter_names.append(node.args.vararg.arg)
    if node.args.kwarg is not None:
        parameter_names.append(node.args.kwarg.arg)
    return parameter_names


def _returns_value(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    if node.returns is None:
        return False
    if isinstance(node.returns, ast.Constant) and node.returns.value is None:
        return False
    return True


def test_source_functions_keep_args_and_returns_docstring_sections() -> None:
    missing_sections: list[str] = []
    for source_path, node in _source_functions():
        docstring = ast.get_docstring(node) or ""
        relative_path = source_path.relative_to(REPO_ROOT)
        meaningful_parameters = _meaningful_parameters(node)
        if not docstring:
            missing_sections.append(f"{relative_path}:{node.lineno}:{node.name}: missing docstring")
            continue
        if meaningful_parameters and "Args:" not in docstring:
            missing_sections.append(f"{relative_path}:{node.lineno}:{node.name}: missing Args")
        if _returns_value(node) and "Returns:" not in docstring:
            missing_sections.append(f"{relative_path}:{node.lineno}:{node.name}: missing Returns")

    assert missing_sections == []


def test_source_functions_do_not_use_bare_star_keyword_only_parameters() -> None:
    keyword_only_functions: list[str] = []
    for source_path, node in _source_functions():
        if node.args.kwonlyargs and node.args.vararg is None:
            relative_path = source_path.relative_to(REPO_ROOT)
            keyword_only_functions.append(f"{relative_path}:{node.lineno}:{node.name}")

    assert keyword_only_functions == []
