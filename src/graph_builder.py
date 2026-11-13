"""Построение графа итеративным DFS без рекурсии."""

from __future__ import annotations

from collections.abc import Callable, Iterable
import json
from pathlib import Path

from .dependency_graph import DependencyGraph
from .repository_reader import MavenRepositoryReader

UNVISITED = 0
ACTIVE = 1
COMPLETE = 2


class GraphBuilder:
    """Строит граф транзитивных зависимостей пакета."""

    def __init__(self, filter_substring: str = ""):
        """Создать построитель с необязательным фильтром пакетов."""
        self.filter_substring = filter_substring

    def _allowed(self, package: str) -> bool:
        """Проверить, проходит ли имя пакета заданный фильтр."""
        return (
            not self.filter_substring
            or self.filter_substring not in package
        )

    def from_test_file(self, path: str, root: str) -> DependencyGraph:
        """Построить граф из локального JSON-файла."""
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"Не удалось прочитать тестовый граф: {exc}"
            ) from exc

        if not isinstance(data, dict) or any(
            not isinstance(key, str)
            or not isinstance(value, list)
            or any(not isinstance(item, str) for item in value)
            for key, value in data.items()
        ):
            raise ValueError(
                'Тестовый JSON должен иметь вид {"A": ["B", "C"]}'
            )

        if root not in data:
            raise ValueError(
                f"Корневой пакет {root!r} отсутствует в тестовом графе"
            )

        graph = DependencyGraph()
        self._dfs(root, lambda node: data.get(node, []), graph)
        return graph

    def from_maven(
        self,
        coordinates: str,
        reader: MavenRepositoryReader,
    ) -> DependencyGraph:
        """Построить граф, загружая POM-файлы из Maven-репозитория."""
        graph = DependencyGraph()
        cache = {}

        def children(node: str) -> list[str]:
            """Получить зависимости узла с локальным кешированием."""
            if node not in cache:
                cache[node] = [
                    dependency.coordinates
                    for dependency in reader.direct_dependencies(node)
                ]
            return cache[node]

        self._dfs(coordinates, children, graph)
        return graph

    def _dfs(
        self,
        root: str,
        get_children: Callable[[str], Iterable[str]],
        graph: DependencyGraph,
    ) -> None:
        """Выполнить итеративный DFS; повторные вершины не раскрывать."""
        if not self._allowed(root):
            return

        state = {root: ACTIVE}  # ACTIVE означает, что вершина в стеке.
        graph.add_node(root)
        stack = [(root, iter(get_children(root)))]

        while stack:
            node, iterator = stack[-1]
            try:
                child = next(iterator)
            except StopIteration:
                state[node] = COMPLETE
                stack.pop()
                continue

            if not self._allowed(child):
                continue

            graph.add_edge(node, child)
            if state.get(child, UNVISITED) == UNVISITED:
                state[child] = ACTIVE
                stack.append((child, iter(get_children(child))))

    @staticmethod
    def installation_order(graph: DependencyGraph) -> list[str]:
        """Вернуть порядок загрузки: сначала зависимости, затем пакеты.

        При обнаружении цикла выбрасывается ValueError, поскольку для
        циклического графа не существует корректного линейного порядка.
        """
        state = {node: UNVISITED for node in graph.adjacency}
        result = []

        for start in graph.adjacency:
            if state[start] != UNVISITED:
                continue

            state[start] = ACTIVE
            stack = [(start, iter(graph.adjacency[start]))]

            while stack:
                node, iterator = stack[-1]
                try:
                    child = next(iterator)
                except StopIteration:
                    state[node] = COMPLETE
                    result.append(node)
                    stack.pop()
                    continue

                if state[child] == ACTIVE:
                    raise ValueError(
                        f"Обнаружен цикл: ребро {node} -> {child}"
                    )

                if state[child] == UNVISITED:
                    state[child] = ACTIVE
                    stack.append((child, iter(graph.adjacency[child])))

        # DFS postorder уже ставит зависимости раньше зависимых пакетов.
        return result
