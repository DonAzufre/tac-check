from __future__ import annotations

from ..tac.ir import Function


def reachable_labels(func: Function) -> set[str]:
    reachable: set[str] = set()

    def dfs(label: str) -> None:
        if label in reachable:
            return
        reachable.add(label)
        for succ in func.blocks[label].successors:
            dfs(succ)

    dfs(func.entry)
    return reachable


def topological_labels(func: Function) -> list[str]:
    """Return a topological order of reachable blocks (assumes loop-free CFG)."""
    visited: set[str] = set()
    order: list[str] = []

    def dfs(label: str) -> None:
        if label in visited:
            return
        visited.add(label)
        for succ in func.blocks[label].successors:
            dfs(succ)
        order.append(label)

    dfs(func.entry)
    return list(reversed(order))
