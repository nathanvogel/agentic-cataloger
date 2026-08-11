"""Unit tests for the contracts StageKind/StageResult vocabulary."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from agentic_cataloger.contracts.models import StageKind, StageResult


def test_stage_kind_values_match_reserved_vocabulary() -> None:
    """StageKind covers discover and assign only."""
    assert {member.value for member in StageKind} == {"discover", "assign"}


def test_stage_result_is_frozen() -> None:
    """StageResult instances cannot be mutated after construction."""
    result = StageResult(
        run_id="run-1",
        stage=StageKind.ASSIGN,
        attempt=1,
        status="success",
    )

    with pytest.raises(FrozenInstanceError):
        result.attempt = 2  # type: ignore[misc]


@pytest.mark.parametrize("status", ["success", "defer", "invalid"])
def test_stage_result_constructs_for_each_status(status: str) -> None:
    """Every status literal constructs a valid StageResult."""
    result = StageResult(
        run_id="run-1",
        stage=StageKind.DISCOVER,
        attempt=1,
        status=status,  # type: ignore[arg-type]
        payload={"note": "example"},
        reason="because" if status != "success" else None,
    )

    assert result.status == status
    assert result.stage is StageKind.DISCOVER
