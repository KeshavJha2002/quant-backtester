from __future__ import annotations

from pathlib import Path

UNIVERSE_ORDER = ("N50", "N150", "N250")


def parse_universe_arg(raw_value: str) -> list[str]:
    normalized = raw_value.strip().upper()
    if normalized == "ALL":
        return list(UNIVERSE_ORDER)
    if normalized not in UNIVERSE_ORDER:
        raise ValueError("universe must be one of: N50, N150, N250, all")
    return [normalized]


def parse_range_arg(raw_value: str) -> tuple[int, int] | None:
    normalized = raw_value.strip().lower()
    if normalized == "all":
        return None

    parts = [part.strip() for part in raw_value.split(",")]
    if len(parts) != 2:
        raise ValueError("range must be 'start,end' or 'all'")

    start = int(parts[0])
    end = int(parts[1])
    if start > end:
        start, end = end, start
    return start, end


def apply_safe_slice(
    tickers: list[str], range_bounds: tuple[int, int] | None
) -> tuple[list[str], tuple[int, int] | None]:
    if range_bounds is None:
        return list(tickers), None

    if not tickers:
        return [], None

    start, end = range_bounds
    clamped_start = max(0, min(start, len(tickers) - 1))
    clamped_end = max(0, min(end, len(tickers) - 1))
    if clamped_start > clamped_end:
        return [], None

    return list(tickers[clamped_start : clamped_end + 1]), (clamped_start, clamped_end)


def slice_label(segment: str, range_bounds: tuple[int, int] | None) -> str:
    if range_bounds is None:
        return segment
    start, end = range_bounds
    return f"{segment} [{start},{end}]"


def update_slice_report(output_path: Path, slice_key: str, slice_report: str, title: str) -> None:
    header = f"# {title}\n"
    begin_marker = f"<!-- BEGIN {slice_key} -->"
    end_marker = f"<!-- END {slice_key} -->"
    wrapped_block = "\n".join([begin_marker, slice_report.rstrip(), end_marker]) + "\n"

    if output_path.exists():
        existing = output_path.read_text(encoding="utf-8")
    else:
        existing = header + "\n"

    if not existing.startswith(header):
        existing = header + "\n"

    start_idx = existing.find(begin_marker)
    end_idx = existing.find(end_marker)
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        end_idx += len(end_marker)
        updated = existing[:start_idx].rstrip() + "\n\n" + wrapped_block + existing[end_idx:]
    else:
        updated = existing.rstrip() + "\n\n" + wrapped_block

    output_path.write_text(updated.rstrip() + "\n", encoding="utf-8")
