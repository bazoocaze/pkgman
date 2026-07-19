"""
ui.py – interactive user interface helpers.
"""

from __future__ import annotations


def prompt_checkbox(
    candidates: list[tuple[str, str, list[str] | str, list[str] | str | None]],
) -> list[tuple[str, str, list[str] | str, list[str] | str | None]]:
    """Show a numbered checkbox list and return selected items.

    Input format: space- or comma-separated numbers, ranges (1-3),
    'all', or empty for none.  Repeat until valid.
    """
    print(f"\nFound {len(candidates)} new manager(s):")
    for i, (mgr_name, exe, _install, _remove) in enumerate(candidates, 1):
        print(f"  [{i}] @{mgr_name:<14} ({exe})")
    print()
    while True:
        answer = input(
            "Select managers to add (numbers, e.g. '1 3' or '1-3' or 'all'): "
        ).strip().lower()
        if answer in ("", "none"):
            return []
        if answer == "all":
            return candidates
        selected: list[int] = []
        try:
            for part in answer.replace(",", " ").split():
                if "-" in part:
                    a, b = part.split("-", 1)
                    selected.extend(range(int(a), int(b) + 1))
                else:
                    selected.append(int(part))
        except ValueError:
            print(f"  Invalid input: '{answer}'. Try again.")
            continue
        selected = sorted(set(selected))
        if not selected or selected[0] < 1 or selected[-1] > len(candidates):
            print(f"  Numbers out of range (1-{len(candidates)}). Try again.")
            continue
        return [candidates[i - 1] for i in selected]


def print_manager_summary(managers: dict) -> None:
    """Print a summary of all registered custom managers."""
    from constants import RESERVED_MANAGERS

    print("\nRegistered custom managers:")
    custom_managers = {
        k: v for k, v in managers.items()
        if k not in RESERVED_MANAGERS
    }
    if not custom_managers:
        print("  (none)")
    else:
        for name, cfg in sorted(custom_managers.items()):
            has_install = "🔧" if cfg.get("install") else "  "
            has_remove = "🗑️" if cfg.get("remove") else "  "
            print(f"  @{name:<12} {has_install} install  {has_remove} remove")