"""Ориентированный граф зависимостей."""

from collections.abc import Iterator
from dataclasses import dataclass, field


@dataclass
class DependencyGraph:
    """Граф, представленный списком смежности."""

    adjacency: dict[str, list[str]] = field(default_factory=dict)

    def add_node(self, node: str) -> None:
        """Добавить вершину, если её ещё нет в графе."""
        self.adjacency.setdefault(node, [])

    def add_edge(self, source: str, target: str) -> None:
        """Добавить направленное ребро от source к target."""
        self.add_node(source)
        self.add_node(target)
        if target not in self.adjacency[source]:
            self.adjacency[source].append(target)

    def nodes(self) -> list[str]:
        """Вернуть список вершин графа."""
        return list(self.adjacency)

    def edges(self) -> Iterator[tuple[str, str]]:
        """Последовательно вернуть все рёбра графа."""
        for source, targets in self.adjacency.items():
            for target in targets:
                yield source, target
