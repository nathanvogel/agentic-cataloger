"""Console entrypoint.

``agentic-cataloger api | worker | migrate | ingest | taxonomy | review | telemetry``.
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from agentic_cataloger.pipeline.ports import Telemetry

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Configure root logging once for the process entrypoint."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )


def _install_early_signal_handlers() -> None:
    """Exit 0 on SIGTERM/SIGINT before a role replaces these handlers.

    ``configure_telemetry`` (Phoenix ``register``) can take longer than a
    readiness probe or PROC test sleep. Without this, the default SIGTERM
    disposition kills the process with return code ``-15``.
    """

    def _handle_shutdown(_signum: int, _frame: object | None) -> None:
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)


def main(argv: list[str] | None = None) -> None:
    """Dispatch ``agentic-cataloger <command>`` to roles or application commands.

    Args:
        argv: CLI arguments. When ``None``, uses ``sys.argv[1:]``.
    """
    _configure_logging()
    _install_early_signal_handlers()
    from agentic_cataloger.platform.telemetry import (
        configure_telemetry,
        shutdown_telemetry,
    )

    telemetry = configure_telemetry()
    try:
        _dispatch_command(list(sys.argv[1:] if argv is None else argv), telemetry)
    finally:
        shutdown_telemetry()


def _dispatch_command(args: list[str], telemetry: Telemetry) -> None:
    """Route top-level CLI argv to the matching command handler.

    Args:
        args: CLI arguments after the program name.
        telemetry: Process-wide telemetry port from bootstrap.

    Raises:
        SystemExit: On help, version, unknown command, or command exit code.
    """
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
    if command in {"-V", "--version"}:
        from importlib.metadata import version

        print(version("agentic-cataloger"))
        raise SystemExit(0)

    exit_code = _dispatch_exit_code_command(command, args[1:], telemetry)
    if exit_code is None:
        logger.error("Unknown command: %s", command)
        _print_help()
        raise SystemExit(1)
    raise SystemExit(exit_code)


def _dispatch_exit_code_command(
    command: str, argv: list[str], telemetry: Telemetry
) -> int | None:
    """Run one exit-code-returning top-level command.

    Args:
        command: Top-level command name (everything but ``api``/``worker``,
            which never return an exit code, and help/version).
        argv: Arguments after the command name.
        telemetry: Process-wide telemetry port from bootstrap.

    Returns:
        The command's exit code, or None when ``command`` is unrecognized.
    """
    if command == "migrate":
        from agentic_cataloger.platform.roles.migrate import run_migrate

        return run_migrate()
    if command == "telemetry":
        return _run_telemetry(argv, telemetry)

    handlers: dict[str, Callable[[list[str]], int]] = {
        "ingest": _run_ingest,
        "run": _run_pipeline,
        "taxonomy": _run_taxonomy,
        "review": _run_review,
    }
    handler = handlers.get(command)
    return handler(argv) if handler is not None else None


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


def _run_pipeline(argv: list[str]) -> int:
    """Parse ``run`` flags and either dry-run select or run the pipeline.

    ``--dry-run`` selects and prints the matching products without making
    any LLM call. Without it, categorizes each selected product through the
    two-stage assign/defer graph (Phase 2 — discover/create lands in
    Phase 3) and prints a run summary.

    Args:
        argv: Arguments after ``run``.

    Returns:
        Process exit code (0 on success).
    """
    parser = argparse.ArgumentParser(
        prog="agentic-cataloger run",
        description=(
            "Select products via IngestFilter and categorize them through "
            "the two-stage discover/assign pipeline."
        ),
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
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of products to select.",
    )
    parser.add_argument(
        "--reassign",
        action="store_true",
        help="Include products that already have a taxonomy leaf membership.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Select and print the products a run would touch; no LLM calls.",
    )
    parsed = parser.parse_args(argv)

    from agentic_cataloger.catalog.ingest_filter import IngestFilter
    from agentic_cataloger.taxonomy.errors import TaxonomyError

    ingest_filter = IngestFilter(
        source_category=parsed.source_category,
        keyword=parsed.keyword,
    )

    if parsed.dry_run:
        from agentic_cataloger.platform.pipeline.runner import run_select_products

        result = run_select_products(
            ingest_filter=ingest_filter,
            limit=parsed.limit,
            unassigned_only=not parsed.reassign,
        )
        for product in result.products:
            print(f"{product.name} [{product.product_id}]")
        print(f"{len(result.products)} product(s) selected")
        return 0

    from agentic_cataloger.platform.pipeline.runner import run_pipeline

    try:
        summary = run_pipeline(
            ingest_filter=ingest_filter,
            limit=parsed.limit,
            unassigned_only=not parsed.reassign,
        )
    except TaxonomyError as exc:
        logger.warning("%s", exc)
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (ValueError, LookupError, RuntimeError) as exc:
        logger.exception("run command failed")
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(
        f"run ok: {summary.product_count} products, "
        f"{summary.deferred_count} deferred, "
        f"{summary.created_count} created, "
        f"{summary.disagreement_count} assign/discover disagreements"
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

    from agentic_cataloger.taxonomy.models import CHILDREN_LIMIT

    children_p = sub.add_parser(
        "children", help="List immediate children of a category (or roots)"
    )
    children_p.add_argument(
        "--parent",
        type=UUID,
        default=None,
        help="Parent category UUID (omit to list root categories)",
    )
    children_p.add_argument(
        "--limit",
        type=int,
        default=None,
        help=f"Max children (default/hard cap {CHILDREN_LIMIT})",
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
    handlers = {
        "create": _do_create_category,
        "reparent": _do_reparent_category,
        "show": _do_show_taxonomy,
        "search": _do_search_categories,
        "children": _do_list_category_children,
        "assign": _do_assign_product,
    }
    handler = handlers.get(parsed.subcommand)
    if handler is None:
        msg = f"unknown subcommand {parsed.subcommand!r}"
        raise ValueError(msg)
    return handler(parsed)


def _do_create_category(parsed: argparse.Namespace) -> int:
    from agentic_cataloger.platform.taxonomy.runner import run_create_category

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


def _do_reparent_category(parsed: argparse.Namespace) -> int:
    from agentic_cataloger.platform.taxonomy.runner import run_reparent_category

    result = run_reparent_category(
        category_id=parsed.category,
        new_parent_id=parsed.parent,
    )
    cat = result.category
    print(f"reparented {cat.name} [{cat.id}] parent={cat.parent_id}")
    return 0


def _do_show_taxonomy(_parsed: argparse.Namespace) -> int:
    from agentic_cataloger.platform.taxonomy.runner import (
        format_taxonomy_tree,
        run_show_taxonomy,
    )

    print(format_taxonomy_tree(run_show_taxonomy()))
    return 0


def _do_search_categories(parsed: argparse.Namespace) -> int:
    from agentic_cataloger.platform.taxonomy.runner import run_search_categories

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
            print(f"  ... {match.child_count - len(match.children)} more, not shown")
    return 0


def _do_list_category_children(parsed: argparse.Namespace) -> int:
    from agentic_cataloger.platform.taxonomy.runner import run_list_category_children

    result = run_list_category_children(parent_id=parsed.parent, limit=parsed.limit)
    if not result.children:
        print("no children")
        return 0
    for child in result.children:
        print(f"{child.name} [{child.id}]")
    if result.child_count > len(result.children):
        print(f"... {result.child_count - len(result.children)} more, not shown")
    return 0


def _do_assign_product(parsed: argparse.Namespace) -> int:
    from agentic_cataloger.platform.taxonomy.runner import (
        ProductRef,
        run_assign_product,
    )

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


def _run_review(argv: list[str]) -> int:
    """Dispatch ``agentic-cataloger review <subcommand>``.

    Args:
        argv: Arguments after ``review``.

    Returns:
        Process exit code (0 on success).
    """
    parser = argparse.ArgumentParser(
        prog="agentic-cataloger review",
        description=(
            "Record and list deferred_items — products an agent stage "
            "won't guess about, awaiting human review."
        ),
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)

    defer_p = sub.add_parser(
        "defer", help="Record that an agent stage won't guess about a product"
    )
    defer_p.add_argument(
        "--product-id", type=UUID, required=True, help="Catalog product UUID"
    )
    defer_p.add_argument(
        "--stage",
        required=True,
        choices=("discover", "assign"),
        help="Pipeline stage that deferred",
    )
    defer_p.add_argument(
        "--reason-code",
        required=True,
        choices=("unknown", "defer", "low_confidence"),
        help="Why the stage declined to produce an outcome",
    )
    defer_p.add_argument(
        "--attempt-count",
        type=int,
        required=True,
        help="How many attempts led to this deferral (>= 1)",
    )
    defer_p.add_argument(
        "--payload",
        required=True,
        help="JSON object: stage-specific payload snapshot",
    )
    defer_p.add_argument(
        "--evidence-span",
        default=None,
        help="Optional source-text evidence span",
    )
    defer_p.add_argument(
        "--trace-id",
        default=None,
        help="Optional Phoenix/OpenTelemetry trace id",
    )

    sub.add_parser("list", help="List every open deferred item")

    parsed = parser.parse_args(argv)

    from agentic_cataloger.review.errors import ReviewError

    try:
        return _dispatch_review(parsed)
    except ReviewError as exc:
        logger.warning("%s", exc)
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (ValueError, TypeError, LookupError, RuntimeError) as exc:
        logger.exception("review command failed")
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _dispatch_review(parsed: argparse.Namespace) -> int:
    """Run one review subcommand.

    Returns:
        Process exit code (0 on success).

    Raises:
        ValueError: Unknown subcommand.
    """
    handlers = {
        "defer": _do_defer_item,
        "list": _do_list_deferred_items,
    }
    handler = handlers.get(parsed.subcommand)
    if handler is None:
        msg = f"unknown subcommand {parsed.subcommand!r}"
        raise ValueError(msg)
    return handler(parsed)


def _do_defer_item(parsed: argparse.Namespace) -> int:
    from agentic_cataloger.contracts.models import StageKind
    from agentic_cataloger.platform.review.runner import run_defer_item
    from agentic_cataloger.review.commands import DeferItemRequest
    from agentic_cataloger.review.models import ReasonCode

    try:
        payload = json.loads(parsed.payload)
    except json.JSONDecodeError as exc:
        msg = f"--payload must be valid JSON: {exc}"
        raise ValueError(msg) from exc
    if not isinstance(payload, dict):
        msg = "--payload must be a JSON object"
        raise TypeError(msg)

    result = run_defer_item(
        DeferItemRequest(
            product_id=parsed.product_id,
            stage=StageKind(parsed.stage),
            reason_code=ReasonCode(parsed.reason_code),
            attempt_count=parsed.attempt_count,
            payload_snapshot=payload,
            evidence_span=parsed.evidence_span,
            trace_id=parsed.trace_id,
        )
    )
    item = result.item
    print(
        f"deferred product={item.product_id} stage={item.stage} "
        f"reason_code={item.reason_code} attempt_count={item.attempt_count} "
        f"[{item.id}]"
    )
    return 0


def _do_list_deferred_items(_parsed: argparse.Namespace) -> int:
    from agentic_cataloger.platform.review.runner import run_list_deferred_items

    result = run_list_deferred_items()
    if not result.items:
        print("no open deferred items")
        return 0
    for item in result.items:
        print(
            f"{item.stage} {item.reason_code} product={item.product_id} "
            f"attempt_count={item.attempt_count} payload={item.payload_snapshot} "
            f"[{item.id}]"
        )
    return 0


def _run_telemetry(argv: list[str], telemetry: Telemetry) -> int:
    """Dispatch ``agentic-cataloger telemetry <subcommand>``.

    Args:
        argv: Arguments after ``telemetry``.
        telemetry: Process-wide telemetry port.

    Returns:
        Process exit code (0 on success).
    """
    parser = argparse.ArgumentParser(
        prog="agentic-cataloger telemetry",
        description=(
            "Telemetry helpers. Requires OPENROUTER_API_KEY for smoke. "
            "Set PHOENIX_COLLECTOR_ENDPOINT (e.g. http://localhost:3022) "
            "to export spans to Phoenix."
        ),
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)
    sub.add_parser(
        "smoke",
        help="Cheap OpenRouter call + leaf LLM span (prints trace_id)",
    )
    parser.parse_args(argv)

    from agentic_cataloger.platform.llm.openrouter import run_telemetry_smoke

    try:
        trace_id = run_telemetry_smoke(telemetry)
    except ValueError as exc:
        logger.error("%s", exc)  # ruff: ignore[error-instead-of-exception] — expected missing-key path
        return 1
    print(f"trace_id={trace_id or 'none'}")
    return 0


def _print_help() -> None:
    """Print CLI usage for supported commands."""
    print(
        "usage: agentic-cataloger <command>\n\n"
        "commands:\n"
        "  api       HTTP server on 0.0.0.0:3020 (/health, /ready)\n"
        "  worker    long-running job consumer stub\n"
        "  migrate   one-shot bootstrap (schema + vendor setup)\n"
        "  ingest    import latest retailer CSVs into the catalog\n"
        "  run       categorize products via the two-stage assign/discover "
        "pipeline (--dry-run to preview, --reassign to re-run assigned products)\n"
        "  taxonomy  create|reparent|show|assign|search|children "
        "substitutability categories\n"
        "  review    defer|list deferred_items for human review\n"
        "  telemetry smoke — cheap OpenRouter call + Phoenix leaf LLM span\n"
    )


if __name__ == "__main__":
    main()
