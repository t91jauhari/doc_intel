"""Prevent HTTP dependencies from leaking back into application use cases."""

import ast
from pathlib import Path


def test_application_operations_do_not_depend_on_http_or_api_modules():
    root = Path(__file__).parents[1] / "app/application"
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith(
                    ("fastapi", "starlette", "app.api", "app.security", "app.domain")
                ), path.name
            if isinstance(node, ast.FunctionDef) or isinstance(
                node, ast.AsyncFunctionDef
            ):
                assert not node.decorator_list, path.name


def test_case_document_and_field_commands_are_thin_http_adapters():
    root = Path(__file__).parents[1] / "app/api"
    for name in (
        "cases",
        "field_processing",
        "administration",
        "notifications",
        "operations",
        "intake",
    ):
        tree = ast.parse((root / (name + ".py")).read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert len(node.body) == 1 and isinstance(node.body[0], ast.Return), (
                    name,
                    node.name,
                )
