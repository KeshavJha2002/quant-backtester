from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trading_bot.monitor.common import (
    evaluate_combination_position,
    format_position_decisions_markdown,
    normalize_ticker,
)


def read_pairs_from_csv(path: Path) -> list[tuple[str, int]]:
    pairs: list[tuple[str, int]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for row_number, row in enumerate(reader, start=1):
            if not row or all(not value.strip() for value in row):
                continue
            if len(row) < 2:
                raise ValueError(f"Row {row_number} in {path} must have ticker,strategy_no")
            pairs.append((normalize_ticker(row[0]), int(row[1])))
    return pairs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv",
        default="hold.csv",
        help="Path to a headerless CSV with rows like TICKER,STRATEGY_NO. Defaults to hold.csv",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    pairs = read_pairs_from_csv(csv_path)
    if not pairs:
        raise SystemExit(f"No valid rows found in {csv_path}")

    decisions = [
        evaluate_combination_position(ticker, strategy_no) for ticker, strategy_no in pairs
    ]
    print(format_position_decisions_markdown(decisions))


if __name__ == "__main__":
    main()
