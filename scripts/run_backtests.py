from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

TEST_REGISTRY = {
    "standalone": {
        1: "research.backtests.standalone.test_s1_tema_macd",
        2: "research.backtests.standalone.test_s2_trend_supertrend",
        3: "research.backtests.standalone.test_s3_projection_cone",
    },
    "combination": {
        1: "research.backtests.combination.test_c1_tema_macd_d_in_w",
        2: "research.backtests.combination.test_c2_trend_supertrend_d_in_w",
        3: "research.backtests.combination.test_c3_tema_macd_d_in_w_projection_cone_d",
        4: "research.backtests.combination.test_c4_trend_supertrend_d_in_w_projection_cone_d",
        5: "research.backtests.combination.test_c5_tema_macd_w_projection_cone_w",
        6: "research.backtests.combination.test_c6_trend_supertrend_w_projection_cone_w",
        7: "research.backtests.combination.test_c7_quantum_supertrend_mtf_projection_cone_d",
    },
}


def parse_strategy_values(raw_values: list[str]) -> list[int]:
    strategies: list[int] = []
    for raw_value in raw_values:
        strategies.extend(int(part.strip()) for part in raw_value.split(",") if part.strip())
    return sorted(dict.fromkeys(strategies))


def build_command(module_name: str, args: argparse.Namespace) -> list[str]:
    command = [sys.executable, "-m", module_name]
    if args.refresh_data:
        command.append("--refresh-data")

    if module_name == "research.backtests.standalone.test_s3_projection_cone":
        command.extend(["--forward-bars-d", str(args.forward_bars_d)])
        command.extend(["--forward-bars-w", str(args.forward_bars_w)])

    if module_name in {
        "research.backtests.combination.test_c3_tema_macd_d_in_w_projection_cone_d",
        "research.backtests.combination.test_c4_trend_supertrend_d_in_w_projection_cone_d",
    }:
        command.extend(["--min-negative-sigma", str(args.min_negative_sigma)])
        command.extend(["--chunk-size", str(args.chunk_size)])
        command.extend(["--max-workers", str(args.max_workers)])
        command.extend(["--universe", args.universe])
        command.extend(["--range", args.range_value])

    return command


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["standalone", "combination"])
    parser.add_argument("--strategy", required=True, nargs="+")
    parser.add_argument("--refresh-data", action="store_true")
    parser.add_argument("--min-negative-sigma", type=float, default=-1.0)
    parser.add_argument("--forward-bars-d", type=int, default=20)
    parser.add_argument("--forward-bars-w", type=int, default=8)
    parser.add_argument("--chunk-size", type=int, default=10)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--universe", default="all")
    parser.add_argument("--range", dest="range_value", default="all")
    args = parser.parse_args()

    strategies = parse_strategy_values(args.strategy)
    registry = TEST_REGISTRY[args.mode]

    for strategy_number in strategies:
        module_name = registry.get(strategy_number)
        if module_name is None:
            raise ValueError(f"Unknown strategy number {strategy_number} for mode {args.mode}")

        print(f"\n=== Running {args.mode} strategy {strategy_number} ===")
        subprocess.run(build_command(module_name, args), check=True, cwd=ROOT)


if __name__ == "__main__":
    main()
