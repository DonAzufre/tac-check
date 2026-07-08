from __future__ import annotations

from ..tac.ir import Function


def reachable_labels(func: Function) -> set[str]:
    reachable: set[str] = set()

    def dfs(label: str) -> None:
        if label in reachable or label not in func.blocks:
            return
        reachable.add(label)
        for succ in func.blocks[label].successors:
            dfs(succ)

    dfs(func.entry)
    return reachable


def topological_labels(func: Function) -> list[str]:
    """Return a DFS postorder-derived order of reachable blocks.

    The project still assumes loop-free v2 examples for precise CFG data-flow.  This
    helper tolerates cycles by not revisiting blocks; loop handling remains bounded by
    the interpreter/model max-step controls.
    """
    visited: set[str] = set()
    order: list[str] = []

    def dfs(label: str) -> None:
        if label in visited or label not in func.blocks:
            return
        visited.add(label)
        for succ in func.blocks[label].successors:
            dfs(succ)
        order.append(label)

    dfs(func.entry)
    return list(reversed(order))
