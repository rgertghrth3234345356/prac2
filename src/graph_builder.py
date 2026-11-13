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

    def allows(self, package: str) -> bool:
        """Проверить, проходит ли имя пакета заданный фильтр."""
        return (
            not self.filter_substring
            or self.filter_substring not in package
        )

    @staticmethod
    def _load_test_data(path: str) -> dict[str, list[str]]:
        """Прочитать и проверить формат тестового JSON-репозитория."""
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"Не удалось прочитать тестовый граф: {exc}"
            ) from exc

        valid = isinstance(data, dict) and all(
            isinstance(key, str)
            and key.isascii()
            and key.isalpha()
            and key.isupper()
            and isinstance(value, list)
            and all(
                isinstance(item, str)
                and item.isascii()
                and item.isalpha()
                and item.isupper()
                for item in value
            )
            for key, value in data.items()
        )
        if valid:
            valid = all(
                dependency in data
                for dependencies in data.values()
                for dependency in dependencies
            )
        if not valid:
            raise ValueError(
                "Имена пакетов тестового JSON должны состоять "
                "только из больших латинских букв, а каждый пакет "
                "из списка зависимостей должен иметь собственную запись; "
                'формат: {"A": ["B", "C"], "B": [], "C": []}'
            )
        return data

    def from_test_file(self, path: str, root: str) -> DependencyGraph:
        """Построить граф из локального JSON-файла."""
        data = self._load_test_data(path)
        if root not in data:
            raise ValueError(
                f"Корневой пакет {root!r} отсутствует в тестовом графе"
            )

        graph = DependencyGraph()
        self._dfs(root, lambda node: data.get(node, []), graph)
        return graph

    def direct_test_dependencies(self, path: str, root: str) -> list[str]:
        """Вернуть прямые зависимости вершины из тестового JSON."""
        data = self._load_test_data(path)
        if root not in data:
            raise ValueError(
                f"Корневой пакет {root!r} отсутствует в тестовом графе"
            )
        return [item for item in data[root] if self.allows(item)]

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
                dependencies = reader.direct_dependencies(node)
                cache[node] = [
                    dependency.coordinates
                    for dependency in dependencies
                    if node == coordinates or not dependency.optional
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
        if not self.allows(root):
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

            if not self.allows(child):
                continue

            graph.add_edge(node, child)
            if state.get(child, UNVISITED) == UNVISITED:
                state[child] = ACTIVE
                stack.append((child, iter(get_children(child))))

    @staticmethod
    def _append_component_order(
        start: str,
        graph: DependencyGraph,
        state: dict[str, int],
        result: list[str],
    ) -> None:
        """Обойти одну компоненту DFS и добавить её в postorder."""
        state[start] = ACTIVE
        active_path = [start]
        active_positions = {start: 0}
        stack = [(start, iter(graph.adjacency[start]))]

        while stack:
            node, iterator = stack[-1]
            try:
                child = next(iterator)
            except StopIteration:
                state[node] = COMPLETE
                result.append(node)
                stack.pop()
                active_positions.pop(node)
                active_path.pop()
                continue

            if state[child] == ACTIVE:
                cycle_start = active_positions[child]
                cycle = active_path[cycle_start:] + [child]
                raise ValueError("Обнаружен цикл: " + " -> ".join(cycle))

            if state[child] == UNVISITED:
                state[child] = ACTIVE
                active_positions[child] = len(active_path)
                active_path.append(child)
                stack.append((child, iter(graph.adjacency[child])))

    @staticmethod
    def installation_order(graph: DependencyGraph) -> list[str]:
        """Вернуть порядок загрузки: сначала зависимости, затем пакеты.

        Для циклического графа линейный порядок невозможен; в сообщении
        об ошибке указывается полный путь обнаруженного цикла.
        """
        state = {node: UNVISITED for node in graph.adjacency}
        result = []
        for start in graph.adjacency:
            if state[start] == UNVISITED:
                GraphBuilder._append_component_order(
                    start, graph, state, result
                )
        return result
