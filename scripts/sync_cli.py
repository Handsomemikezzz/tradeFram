from __future__ import annotations

import argparse


def add_price_adjustment_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--price-adjustment",
        action="append",
        choices=["raw", "qfq", "hfq"],
        default=None,
        dest="price_adjustment",
        help="Daily bar adjustment to sync. Repeat for multiple. Default: raw + qfq.",
    )


def parse_price_adjustments(raw: list[str] | None) -> tuple[str, ...]:
    if not raw:
        return ("raw", "qfq")
    return tuple(raw)
