"""Генерация Mermaid- и ASCII-представлений графа."""

from .dependency_graph import DependencyGraph



class GraphVisualizer:
    """Преобразует граф зависимостей в текстовые схемы."""

    @staticmethod
    def to_mermaid(graph: DependencyGraph) -> str:
        """Вернуть описание графа в формате Mermaid с безопасными ID."""
        nodes = graph.nodes()
        identifiers = {
            node: f"node_{index}" for index, node in enumerate(nodes)
        }
        lines = ["flowchart TD"]

        for node in nodes:
            label = node.replace("&", "&amp;").replace('"', "&quot;")
            lines.append(f'    {identifiers[node]}["{label}"]')

        for source, target in graph.edges():
            lines.append(
                f"    {identifiers[source]} --> {identifiers[target]}"
            )
        return "\n".join(lines)

    @staticmethod
    def to_ascii(graph: DependencyGraph, root: str) -> str:
        """Вернуть ASCII-дерево с сохранением исходного порядка ветвей."""
        if root not in graph.adjacency:
            return root

        lines = [root]
        # Записи добавляются в результат при извлечении из стека.
        stack = []
        children = graph.adjacency.get(root, [])
        for index in range(len(children) - 1, -1, -1):
            child = children[index]
            is_last = index == len(children) - 1
            branch = "`-- " if is_last else "|-- "
            extension = "    " if is_last else "|   "
            stack.append((child, extension, branch, frozenset({root})))

        while stack:
            node, prefix, branch, path = stack.pop()
            lines.append(prefix[:-4] + branch + node)
            if node in path:
                lines[-1] += " (цикл)"
                continue

            next_path = path | {node}
            descendants = graph.adjacency.get(node, [])
            for index in range(len(descendants) - 1, -1, -1):
                child = descendants[index]
                is_last = index == len(descendants) - 1
                child_branch = "`-- " if is_last else "|-- "
                extension = "    " if is_last else "|   "
                stack.append(
                    (child, prefix + extension, child_branch, next_path)
                )

        return "\n".join(lines)
