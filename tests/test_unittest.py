"""Дополнительные тесты приложения с использованием unittest."""

import json
import tempfile
import unittest
from pathlib import Path

from src.argument_parser import parse_args
from src.dependency_graph import DependencyGraph
from src.graph_builder import GraphBuilder
from src.graph_visualizer import GraphVisualizer


class DependencyGraphTests(unittest.TestCase):
    """Проверки построения графа, сортировки и визуализации."""

    def test_dfs_cycle_and_visualization(self):
        """Проверить DFS, сохранение цикла и визуализацию."""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "graph.json"
            path.write_text(
                json.dumps(
                    {"A": ["B"], "B": ["A", "C"], "C": []}
                ),
                encoding="utf-8",
            )
            graph = GraphBuilder().from_test_file(str(path), "A")

        self.assertEqual(set(graph.nodes()), {"A", "B", "C"})
        self.assertIn("-->", GraphVisualizer.to_mermaid(graph))
        self.assertIn("(цикл)", GraphVisualizer.to_ascii(graph, "A"))

    def test_topological_order(self):
        """Проверить, что зависимости идут раньше зависимых пакетов."""
        graph = DependencyGraph({"A": ["B"], "B": []})
        order = GraphBuilder.installation_order(graph)

        self.assertLess(order.index("B"), order.index("A"))

    def test_test_mode_accepts_uppercase_vertex(self):
        """Проверить разбор аргументов тестового режима."""
        config = parse_args(
            [
                "--package",
                "A",
                "--repository",
                "test-repository.json",
                "--test-mode",
            ]
        )

        self.assertEqual(config.package, "A")


if __name__ == "__main__":
    unittest.main()
