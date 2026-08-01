"""Console entrypoint: `pricecomp api | worker | migrate`."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        _print_help()
        raise SystemExit(0 if args and args[0] in {"-h", "--help"} else 1)

    role = args[0]
    if role == "api":
        from pricecomp.platform.roles.api import run_api

        run_api()
        return
    if role == "worker":
        from pricecomp.platform.roles.worker import run_worker

        run_worker()
        return
    if role == "migrate":
        from pricecomp.platform.roles.migrate import run_migrate

        raise SystemExit(run_migrate())
    if role in {"-V", "--version"}:
        from importlib.metadata import version

        print(version("pricecomp"))
        raise SystemExit(0)

    print(f"Unknown role: {role}", file=sys.stderr)
    _print_help()
    raise SystemExit(1)


def _print_help() -> None:
    print(
        "usage: pricecomp <role>\n\n"
        "roles:\n"
        "  api      HTTP server on 0.0.0.0:3020 (/health, /ready)\n"
        "  worker   long-running job consumer stub\n"
        "  migrate  one-shot bootstrap (schema + vendor setup)\n"
    )


if __name__ == "__main__":
    main()