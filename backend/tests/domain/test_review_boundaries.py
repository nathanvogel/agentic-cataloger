"""Review package must stay free of persistence / framework imports."""

from __future__ import annotations

import ast
from pathlib import Path

REVIEW_ROOT = (
    Path(__file__).resolve().parents[2] / "src" / "agentic_cataloger" / "review"
)
FORBIDDEN = {
    "psycopg",
    "sqlalchemy",
    "alembic",
    "fastapi",
    "langchain",
    "langgraph",
    "opentelemetry",
}


def test_review_root_contains_python_modules() -> None:
    assert REVIEW_ROOT.is_dir()
    py_files = list(REVIEW_ROOT.rglob("*.py"))
    assert py_files, f"no Python files under {REVIEW_ROOT}"


def test_review_has_no_adapter_imports() -> None:
    """No review module may import platform adapters or SQL libraries."""
    offenders: list[str] = []
    for path in REVIEW_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            for name in names:
                if name in FORBIDDEN or name == "agentic_cataloger.platform":
                    offenders.append(f"{path.name}: {name}")
                if (
                    name == "agentic_cataloger"
                    and isinstance(node, ast.ImportFrom)
                    and node.module
                    and node.module.startswith("agentic_cataloger.platform")
                ):
                    offenders.append(f"{path.name}: {node.module}")
    assert offenders == []
