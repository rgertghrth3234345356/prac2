"""Тесты построения и визуализации графа зависимостей."""

import json

import pytest

from src.dependency_graph import DependencyGraph
from src.graph_builder import GraphBuilder
from src.graph_visualizer import GraphVisualizer


def test_transitive_graph_and_cycle(tmp_path):
    """Проверить построение транзитивного графа с циклом."""
    graph_file = tmp_path / "graph.json"
    graph_file.write_text(
        json.dumps(
            {
                "A": ["B"],
                "B": ["C"],
                "C": ["A", "D"],
                "D": [],
            }
        ),
        encoding="utf-8",
    )
    graph = GraphBuilder().from_test_file(str(graph_file), "A")

    assert graph.adjacency["C"] == ["A", "D"]
    assert set(graph.nodes()) == {"A", "B", "C", "D"}


def test_filter(tmp_path):
    """Проверить исключение вершин по фильтру подстроки."""
    graph_file = tmp_path / "graph.json"
    graph_file.write_text(
        json.dumps({"A": ["BTEST", "C"], "BTEST": [], "C": []}),
        encoding="utf-8",
    )
    graph = GraphBuilder("TEST").from_test_file(str(graph_file), "A")

    assert "BTEST" not in graph.adjacency["A"]


def test_mermaid_and_ascii():
    """Проверить генерацию Mermaid и ASCII-представления."""
    graph = DependencyGraph({"A": ["B", "C"], "B": [], "C": []})
    mermaid = GraphVisualizer.to_mermaid(graph)

    assert "flowchart TD" in mermaid and "-->" in mermaid

    ascii_tree = GraphVisualizer.to_ascii(graph, "A")
    assert "A" in ascii_tree and "B" in ascii_tree and "C" in ascii_tree


def test_ascii_preserves_dependency_order():
    """Проверить порядок ветвей ASCII-дерева по исходному графу."""
    graph = DependencyGraph({"A": ["B", "C"], "B": [], "C": []})
    result = GraphVisualizer.to_ascii(graph, "A")

    assert result.index("B") < result.index("C")


def test_ascii_marks_cycle_without_infinite_traversal():
    """Проверить маркировку циклического ребра в ASCII-дереве."""
    graph = DependencyGraph({"A": ["B"], "B": ["A"]})
    result = GraphVisualizer.to_ascii(graph, "A")

    assert "A (цикл)" in result


def test_test_repository_requires_uppercase_latin_names(tmp_path):
    """Проверить ограничение формата имён тестовых пакетов."""
    graph_file = tmp_path / "graph.json"
    graph_file.write_text(json.dumps({"A": ["lowercase"]}), encoding="utf-8")

    with pytest.raises(ValueError, match="больших латинских букв"):
        GraphBuilder().from_test_file(str(graph_file), "A")


def test_direct_test_dependencies_and_filter(tmp_path):
    """Проверить вывод только прямых зависимостей и фильтрацию."""
    graph_file = tmp_path / "graph.json"
    graph_file.write_text(
        json.dumps({"A": ["B", "TEST"], "B": [], "TEST": []}),
        encoding="utf-8",
    )

    dependencies = GraphBuilder("TEST").direct_test_dependencies(
        str(graph_file), "A"
    )
    assert dependencies == ["B"]


def test_test_repository_rejects_undefined_dependency(tmp_path):
    """Проверить, что каждая зависимость описана отдельной вершиной."""
    graph_file = tmp_path / "graph.json"
    graph_file.write_text(json.dumps({"A": ["B"]}), encoding="utf-8")

    with pytest.raises(ValueError, match="собственную запись"):
        GraphBuilder().from_test_file(str(graph_file), "A")


def test_optional_dependency_is_not_included_transitively():
    """Optional зависимости корневого пакета включаются, транзитивные — нет."""
    from src.package_info import PackageInfo

    class FakeReader:
        """Возвращает фиксированные зависимости для проверки обхода."""

        def direct_dependencies(self, coordinates):
            if coordinates == "root:app:1.0":
                return [PackageInfo("org", "first", "1.0")]
            if coordinates == "org:first:1.0":
                return [
                    PackageInfo("org", "required", "1.0"),
                    PackageInfo(
                        "org", "optional", "1.0", optional=True
                    ),
                ]
            return []

    graph = GraphBuilder().from_maven("root:app:1.0", FakeReader())

    assert "org:required:1.0" in graph.adjacency["org:first:1.0"]
    assert "org:optional:1.0" not in graph.adjacency["org:first:1.0"]
