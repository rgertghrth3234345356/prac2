"""Точка входа приложения."""

from .argument_parser import parse_args, print_config
from .graph_builder import GraphBuilder
from .graph_visualizer import GraphVisualizer
from .repository_reader import MavenRepositoryReader, RepositoryError


def _build_graph(config, builder: GraphBuilder):
    """Построить граф из тестового JSON или Maven-репозитория."""
    if config.test_mode:
        return builder.from_test_file(config.repository, config.package)
    reader = MavenRepositoryReader(config.repository)
    return builder.from_maven(config.package, reader)


def _print_graph(graph, package: str) -> None:
    """Вывести список вершин и их прямых зависимостей."""
    print(f"Граф зависимостей для {package}:")
    for node, dependencies in graph.adjacency.items():
        dependency_text = ", ".join(dependencies) or "(нет зависимостей)"
        print(f"{node}: {dependency_text}")


def _print_order(builder: GraphBuilder, graph) -> None:
    """Вывести порядок загрузки зависимостей."""
    print("\nПорядок загрузки (сначала зависимости):")
    for index, package in enumerate(
        builder.installation_order(graph),
        start=1,
    ):
        print(f"{index}. {package}")


def _print_direct_dependencies(config, builder: GraphBuilder) -> None:
    """Вывести только непосредственные зависимости указанного пакета."""
    if config.test_mode:
        dependencies = builder.direct_test_dependencies(
            config.repository, config.package
        )
    else:
        reader = MavenRepositoryReader(config.repository)
        dependencies = [
            dependency.coordinates
            for dependency in reader.direct_dependencies(config.package)
            if builder.allows(dependency.coordinates)
        ]

    print(f"Прямые зависимости {config.package}:")
    if not dependencies:
        print("(нет прямых зависимостей)")
        return
    for dependency in dependencies:
        print(f"- {dependency}")


def _print_results(config, builder: GraphBuilder, graph) -> None:
    """Вывести граф и выбранные пользователем представления."""
    _print_graph(graph, config.package)
    print("\nMermaid:")
    print(GraphVisualizer.to_mermaid(graph))
    if config.ascii_tree:
        print("\nASCII-дерево:")
        print(GraphVisualizer.to_ascii(graph, config.package))
    if config.show_order:
        _print_order(builder, graph)


def main(argv=None) -> int:
    """Запустить приложение и вернуть код завершения."""
    config = parse_args(argv)
    if config.show_config:
        print_config(config)

    try:
        builder = GraphBuilder(config.filter_substring)
        if config.direct_only:
            _print_direct_dependencies(config, builder)
            return 0
        graph = _build_graph(config, builder)
        _print_results(config, builder, graph)
    except (RepositoryError, ValueError) as exc:
        print(f"Ошибка: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
