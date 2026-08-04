"""Console entrypoint.

``agentic-cataloger api | worker | migrate | ingest | taxonomy``.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from uuid import UUID

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Configure root logging once for the process entrypoint."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )


def main(argv: list[str] | None = None) -> None:
    """Dispatch ``agentic-cataloger <command>`` to roles or application commands.

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
        from agentic_cataloger.platform.roles.api import run_api

        run_api()
        return
    if command == "worker":
        from agentic_cataloger.platform.roles.worker import run_worker

        run_worker()
        return
    if command == "migrate":
        from agentic_cataloger.platform.roles.migrate import run_migrate

        raise SystemExit(run_migrate())
    if command == "ingest":
        raise SystemExit(_run_ingest(args[1:]))
    if command == "taxonomy":
        raise SystemExit(_run_taxonomy(args[1:]))
    if command in {"-V", "--version"}:
        from importlib.metadata import version

        print(version("agentic-cataloger"))
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
        prog="agentic-cataloger ingest",
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
    parser.add_argument(
        "--source-category",
        default=None,
        help=(
            "Filter: case-insensitive substring of source_category, or exact "
            "match of unified_category (e.g. Milchprodukte or dairy)."
        ),
    )
    parser.add_argument(
        "--keyword",
        default=None,
        help="Filter: case-insensitive substring of product name / name_de.",
    )
    parsed = parser.parse_args(argv)

    from agentic_cataloger.catalog.ingest_filter import IngestFilter
    from agentic_cataloger.platform.ingest.runner import run_ingest

    data_dir = parsed.data_dir
    if data_dir is None:
        # backend/src/agentic_cataloger/platform/cli.py → parents[4] = repo root
        data_dir = Path(__file__).resolve().parents[4] / "data"

    retailers = tuple(parsed.retailers) if parsed.retailers else None
    ingest_filter = IngestFilter(
        source_category=parsed.source_category,
        keyword=parsed.keyword,
    )
    summary = run_ingest(
        data_dir=data_dir,
        retailers=retailers,
        ingest_filter=ingest_filter,
    )
    print(
        f"ingest ok: snapshots={summary.snapshot_count} "
        f"upserted={summary.upserted_count} "
        f"matched={summary.matched_count} "
        f"filtered_out={summary.filtered_out_count} "
        f"deferred={summary.deferred_count} "
        f"collisions={summary.collision_count}"
    )
    return 0


def _run_taxonomy(argv: list[str]) -> int:
    """Dispatch ``agentic-cataloger taxonomy <subcommand>``.

    Args:
        argv: Arguments after ``taxonomy``.

    Returns:
        Process exit code (0 on success).
    """
    parser = argparse.ArgumentParser(
        prog="agentic-cataloger taxonomy",
        description=(
            "Manage the substitutability category tree and product↔leaf "
            "membership. Categories are identified by UUID (see ``show``). "
            "Retailer source_category fields stay on catalog products only."
        ),
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)

    create_p = sub.add_parser("create", help="Create a root or child category")
    create_p.add_argument("--name", required=True, help="Category display name")
    create_p.add_argument(
        "--parent",
        type=UUID,
        default=None,
        help="Parent category UUID (omit to create the root)",
    )
    create_p.add_argument(
        "--unit",
        default=None,
        dest="preferred_comparable_unit",
        help="Optional preferred_comparable_unit (stored, not validated)",
    )

    reparent_p = sub.add_parser("reparent", help="Move a category under a new parent")
    reparent_p.add_argument(
        "--category",
        type=UUID,
        required=True,
        help="Category UUID to move",
    )
    reparent_p.add_argument(
        "--parent",
        type=UUID,
        required=True,
        help="New parent category UUID",
    )

    sub.add_parser("show", help="Print the rooted taxonomy tree")

    from agentic_cataloger.taxonomy.commands import (
        DEFAULT_SEARCH_RESULTS,
        MAX_SEARCH_RESULTS,
    )

    search_p = sub.add_parser("search", help="Fuzzy-search categories by name")
    search_p.add_argument("--query", required=True, help="Search text")
    search_p.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            f"Max results (default {DEFAULT_SEARCH_RESULTS}, "
            f"hard cap {MAX_SEARCH_RESULTS})"
        ),
    )

    assign_p = sub.add_parser(
        "assign",
        help="Assign a product to a leaf (moves on re-assign)",
    )
    assign_p.add_argument(
        "--leaf",
        type=UUID,
        required=True,
        help="Leaf category UUID",
    )
    assign_p.add_argument(
        "--product-id",
        type=UUID,
        default=None,
        help="Catalog product UUID",
    )
    assign_p.add_argument(
        "--namespace",
        default=None,
        help="Source namespace (e.g. migros-ch); use with --source-product-id",
    )
    assign_p.add_argument(
        "--source-product-id",
        default=None,
        help="Retailer product id; use with --namespace",
    )
    assign_p.add_argument(
        "--variant",
        default=None,
        dest="source_variant_id",
        help="Optional source variant id",
    )

    parsed = parser.parse_args(argv)

    from agentic_cataloger.taxonomy.errors import TaxonomyError

    try:
        return _dispatch_taxonomy(parsed)
    except TaxonomyError as exc:
        logger.warning("%s", exc)
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (ValueError, LookupError, RuntimeError) as exc:
        logger.exception("taxonomy command failed")
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _dispatch_taxonomy(parsed: argparse.Namespace) -> int:
    """Run one taxonomy subcommand.

    Returns:
        Process exit code (0 on success).

    Raises:
        ValueError: Unknown subcommand.
    """
    from agentic_cataloger.platform.taxonomy.runner import (
        ProductRef,
        format_taxonomy_tree,
        run_assign_product,
        run_create_category,
        run_reparent_category,
        run_search_categories,
        run_show_taxonomy,
    )

    if parsed.subcommand == "create":
        result = run_create_category(
            name=parsed.name,
            parent_id=parsed.parent,
            preferred_comparable_unit=parsed.preferred_comparable_unit,
        )
        cat = result.category
        print(
            f"created {cat.name} [{cat.id}] "
            f"parent={cat.parent_id} unit={cat.preferred_comparable_unit}"
        )
        return 0
    if parsed.subcommand == "reparent":
        result = run_reparent_category(
            category_id=parsed.category,
            new_parent_id=parsed.parent,
        )
        cat = result.category
        print(f"reparented {cat.name} [{cat.id}] parent={cat.parent_id}")
        return 0
    if parsed.subcommand == "show":
        print(format_taxonomy_tree(run_show_taxonomy()))
        return 0
    if parsed.subcommand == "search":
        result = run_search_categories(query=parsed.query, limit=parsed.limit)
        if not result.matches:
            print("no matches")
            return 0
        for match in result.matches:
            cat = match.category
            leaf = "leaf" if match.is_leaf else "non-leaf"
            print(
                f"{cat.name} [{cat.id}] parent={match.parent_name} {leaf} "
                f"score={match.score:.3f} children={match.child_count}"
            )
            for child in match.children:
                print(f"  - {child.name} [{child.id}]")
            if match.child_count > len(match.children):
                print(
                    f"  ... {match.child_count - len(match.children)} more, not shown"
                )
        return 0
    if parsed.subcommand == "assign":
        result = run_assign_product(
            product=ProductRef(
                product_id=parsed.product_id,
                source_namespace=parsed.namespace,
                source_product_id=parsed.source_product_id,
                source_variant_id=parsed.source_variant_id,
            ),
            leaf_id=parsed.leaf,
        )
        membership = result.membership
        moved = "moved" if result.moved else "assigned"
        print(f"{moved} product={membership.product_id} leaf={membership.category_id}")
        return 0

    msg = f"unknown subcommand {parsed.subcommand!r}"
    raise ValueError(msg)


def _print_help() -> None:
    """Print CLI usage for supported commands."""
    print(
        "usage: agentic-cataloger <command>\n\n"
        "commands:\n"
        "  api       HTTP server on 0.0.0.0:3020 (/health, /ready)\n"
        "  worker    long-running job consumer stub\n"
        "  migrate   one-shot bootstrap (schema + vendor setup)\n"
        "  ingest    import latest retailer CSVs into the catalog\n"
        "  taxonomy  create|reparent|show|assign|search substitutability categories\n"
    )


if __name__ == "__main__":
    main()
