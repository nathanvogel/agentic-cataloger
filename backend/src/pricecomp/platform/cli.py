"""Console entrypoint: ``pricecomp api | worker | migrate | ingest``."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Configure root logging once for the process entrypoint."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )


def main(argv: list[str] | None = None) -> None:
    """Dispatch ``pricecomp <command>`` to roles or application commands.

    Args:
        argv: CLI arguments. When ``None``, uses ``sys.argv[1:]``.

    Raises:
        SystemExit: On help, version, unknown command, or command exit code.
    """
    _configure_logging()
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        _print_help()
        raise SystemExit(0 if args and args[0] in {"-h", "--help"} else 1)

    command = args[0]
    if command == "api":
        from pricecomp.platform.roles.api import run_api

        run_api()
        return
    if command == "worker":
        from pricecomp.platform.roles.worker import run_worker

        run_worker()
        return
    if command == "migrate":
        from pricecomp.platform.roles.migrate import run_migrate

        raise SystemExit(run_migrate())
    if command == "ingest":
        raise SystemExit(_run_ingest(args[1:]))
    if command in {"-V", "--version"}:
        from importlib.metadata import version

        print(version("pricecomp"))
        raise SystemExit(0)

    logger.error("Unknown command: %s", command)
    _print_help()
    raise SystemExit(1)


def _run_ingest(argv: list[str]) -> int:
    """Parse ingest flags and run latest-CSV import.

    Args:
        argv: Arguments after ``ingest``.

    Returns:
        Process exit code (0 on success).
    """
    parser = argparse.ArgumentParser(
        prog="pricecomp ingest",
        description=(
            "Register immutable catalog snapshots and upsert products from the "
            "latest CSV per retailer under data/."
        ),
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Path to data/ (default: <repo>/data)",
    )
    parser.add_argument(
        "--retailer",
        action="append",
        dest="retailers",
        choices=("migros", "lidl", "coop", "denner"),
        help="Limit to one or more retailers (repeatable). Default: all.",
    )
    parsed = parser.parse_args(argv)

    from pricecomp.platform.ingest.runner import run_ingest

    data_dir = parsed.data_dir
    if data_dir is None:
        # backend/src/pricecomp/platform/cli.py → parents[4] = repo root
        data_dir = Path(__file__).resolve().parents[4] / "data"

    retailers = tuple(parsed.retailers) if parsed.retailers else None
    summary = run_ingest(data_dir=data_dir, retailers=retailers)
    print(
        f"ingest ok: snapshots={summary.snapshot_count} "
        f"upserted={summary.upserted_count} "
        f"deferred={summary.deferred_count} "
        f"collisions={summary.collision_count}"
    )
    return 0


def _print_help() -> None:
    """Print CLI usage for supported commands."""
    print(
        "usage: pricecomp <command>\n\n"
        "commands:\n"
        "  api      HTTP server on 0.0.0.0:3020 (/health, /ready)\n"
        "  worker   long-running job consumer stub\n"
        "  migrate  one-shot bootstrap (schema + vendor setup)\n"
        "  ingest   import latest retailer CSVs into the catalog\n"
    )


if __name__ == "__main__":
    main()
