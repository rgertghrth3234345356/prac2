"""Тесты этапа 4: порядок загрузки зависимостей."""

import pytest

from src.dependency_graph import DependencyGraph
from src.graph_builder import GraphBuilder


def test_dependencies_are_before_dependent_packages():
    """Зависимости должны появляться раньше использующих их пакетов."""
    graph = DependencyGraph(
        {
            "A": ["B", "C"],
            "B": ["D"],
            "C": ["D"],
            "D": [],
        }
    )
    order = GraphBuilder.installation_order(graph)

    assert order.index("D") < order.index("B") < order.index("A")
    assert order.index("D") < order.index("C") < order.index("A")


def test_installation_order_rejects_cycles():
    """Для циклического графа линейный порядок не должен возвращаться."""
    graph = DependencyGraph({"A": ["B"], "B": ["A"]})

    with pytest.raises(ValueError, match="цикл"):
        GraphBuilder.installation_order(graph)


def test_cycle_error_contains_full_path():
    """Сообщение об ошибке должно показывать последовательность цикла."""
    graph = DependencyGraph({"A": ["B"], "B": ["C"], "C": ["A"]})

    with pytest.raises(ValueError, match="A -> B -> C -> A"):
        GraphBuilder.installation_order(graph)
