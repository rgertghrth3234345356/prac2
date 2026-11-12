"""Генерация Mermaid- и ASCII-представлений графа."""

import re

from .dependency_graph import DependencyGraph


def _mermaid_id(name: str) -> str:
    """Преобразовать имя вершины в допустимый идентификатор Mermaid."""
    safe = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not safe or safe[0].isdigit():
        safe = "n_" + safe
    return safe


class GraphVisualizer:
    """Преобразует граф зависимостей в текстовые схемы."""

    @staticmethod
    def to_mermaid(graph: DependencyGraph) -> str:
        """Вернуть описание графа в формате Mermaid."""
        lines = ["flowchart TD"]
        used = set()

        for source, target in graph.edges():
            source_id = _mermaid_id(source)
            target_id = _mermaid_id(target)
            lines.append(
                f'    {source_id}["{source}"] --> '
                f'{target_id}["{target}"]'
            )
            used.update((source, target))

        for node in graph.nodes():
            if node not in used:
                lines.append(f'    {_mermaid_id(node)}["{node}"]')

        return "\n".join(lines)

    @staticmethod
    def to_ascii(graph: DependencyGraph, root: str) -> str:
        """Вернуть ASCII-дерево зависимостей от корневого пакета."""
        if root not in graph.adjacency:
            return root

        lines = [root]
        # Стек хранит узел, префикс и путь для обнаружения циклов.
        stack = [(root, "", frozenset({root}))]

        while stack:
            node, prefix, path = stack.pop()
            children = graph.adjacency.get(node, [])

            for index in range(len(children) - 1, -1, -1):
                child = children[index]
                last = index == len(children) - 1
                branch = "`-- " if last else "|-- "

                if child in path:
                    lines.append(prefix + branch + f"{child} (цикл)")
                    continue

                lines.append(prefix + branch + child)
                extension = "    " if last else "|   "
                stack.append(
                    (child, prefix + extension, path | {child})
                )

        return "\n".join(lines)
