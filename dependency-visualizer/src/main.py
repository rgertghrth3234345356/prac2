"""Точка входа приложения."""

from .argument_parser import parse_args, print_config
from .graph_builder import GraphBuilder
from .graph_visualizer import GraphVisualizer
from .repository_reader import MavenRepositoryReader, RepositoryError


def main() -> int:
    """Запустить приложение и вернуть код завершения."""
    config = parse_args()

    if config.show_config:
        print_config(config)

    try:
        builder = GraphBuilder(config.filter_substring)

        if config.test_mode:
            graph = builder.from_test_file(
                config.repository,
                config.package,
            )
        else:
            reader = MavenRepositoryReader(config.repository)
            graph = builder.from_maven(config.package, reader)

        print(f"Граф зависимостей для {config.package}:")

        for node, dependencies in graph.adjacency.items():
            deps = (
                ", ".join(dependencies)
                if dependencies
                else "(нет зависимостей)"
            )
            print(f"{node}: {deps}")

        print("\nMermaid:")
        print(GraphVisualizer.to_mermaid(graph))

        if config.ascii_tree:
            print("\nASCII-дерево:")
            print(GraphVisualizer.to_ascii(graph, config.package))

        if config.show_order:
            print("\nПорядок загрузки (сначала зависимости):")
            for index, package in enumerate(
                builder.installation_order(graph),
                start=1,
            ):
                print(f"{index}. {package}")

    except (RepositoryError, ValueError) as exc:
        print(f"Ошибка: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
