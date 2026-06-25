from __future__ import annotations

import ast
import importlib
import inspect
import pkgutil
from pathlib import Path

import ticket_readiness


def test_static_type_checker_is_configured_and_documented():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert '"mypy' in pyproject
    assert "[tool.mypy]" in pyproject
    assert ".venv/bin/python -m mypy src/ticket_readiness" in readme


def test_public_functions_have_return_type_hints():
    missing = []
    for module_info in pkgutil.iter_modules(ticket_readiness.__path__, ticket_readiness.__name__ + "."):
        if module_info.name.endswith(".__main__"):
            continue
        module = importlib.import_module(module_info.name)
        for name, member in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("_"):
                continue
            if getattr(member, "__module__", None) != module.__name__:
                continue
            if inspect.signature(member).return_annotation is inspect.Signature.empty:
                missing.append(f"{module.__name__}.{name}")

    assert missing == []


def test_production_functions_do_not_use_bare_dict_return_annotations():
    missing = []
    for path in sorted(Path("src/ticket_readiness").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and isinstance(node.returns, ast.Name) and node.returns.id == "dict":
                missing.append(f"{path}:{node.lineno}:{node.name}")

    assert missing == []
