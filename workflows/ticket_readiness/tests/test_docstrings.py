from __future__ import annotations

import importlib
import inspect
import pkgutil

import ticket_readiness


COMPLEX_PRIVATE_HELPERS = {
    "ticket_readiness.readiness._custom_check_from_config",
    "ticket_readiness.summary._report_model_metadata",
    "ticket_readiness.workflow._reconstruct_summary_state",
}


def test_public_functions_and_classes_have_docstrings():
    missing = []
    for module_info in pkgutil.iter_modules(ticket_readiness.__path__, ticket_readiness.__name__ + "."):
        if module_info.name.endswith(".__main__"):
            continue
        module = importlib.import_module(module_info.name)
        for name, member in inspect.getmembers(module):
            if name.startswith("_"):
                continue
            if not (inspect.isclass(member) or inspect.isfunction(member)):
                continue
            if getattr(member, "__module__", None) != module.__name__:
                continue
            if not inspect.getdoc(member):
                missing.append(f"{module.__name__}.{name}")

    assert missing == []


def test_complex_private_helpers_have_docstrings():
    missing = []
    for dotted_name in sorted(COMPLEX_PRIVATE_HELPERS):
        module_name, member_name = dotted_name.rsplit(".", 1)
        module = importlib.import_module(module_name)
        if not inspect.getdoc(getattr(module, member_name)):
            missing.append(dotted_name)

    assert missing == []
