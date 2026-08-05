"""Pipeline package must stay free of persistence / framework imports."""

from __future__ import annotations

import ast
from pathlib import Path

PIPELINE_ROOT = (
    Path(__file__).resolve().parents[2] / "src" / "agentic_cataloger" / "pipeline"
)
FORBIDDEN = {
    "psycopg",
    "sqlalchemy",
    "alembic",
    "fastapi",
    "langchain",
    "langgraph",
    "opentelemetry",
    "phoenix",
}


def test_pipeline_root_contains_python_modules() -> None:
    assert PIPELINE_ROOT.is_dir()
    py_files = list(PIPELINE_ROOT.rglob("*.py"))
    assert py_files, f"no Python files under {PIPELINE_ROOT}"


def test_pipeline_has_no_adapter_imports() -> None:
    """No pipeline module may import platform adapters or tracing SDKs."""
    offenders: list[str] = []
    for path in PIPELINE_ROOT.rglob("*.py"):
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
