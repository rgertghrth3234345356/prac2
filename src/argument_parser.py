"""Разбор и проверка аргументов командной строки."""

import argparse
import re
from pathlib import Path
from urllib.parse import urlsplit

from .config import Config


COORDINATE_RE = re.compile(
    r"^[A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+:[A-Za-z0-9_.+-]+"
    r"(?::[A-Za-z0-9_.-]+)?$"
)


def _add_package_arguments(parser: argparse.ArgumentParser) -> None:
    """Добавить аргументы выбора пакета и источника данных."""
    parser.add_argument(
        "--package",
        required=True,
        help="Координаты Maven: groupId:artifactId:version",
    )
    parser.add_argument(
        "--repository",
        required=True,
        help="URL Maven-репозитория или путь к JSON-файлу тестового графа",
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Использовать локальный тестовый репозиторий",
    )


def _add_output_arguments(parser: argparse.ArgumentParser) -> None:
    """Добавить параметры управления выводом программы."""
    parser.add_argument(
        "--ascii",
        action="store_true",
        help="Вывести зависимости в виде ASCII-дерева",
    )
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Вывести только прямые зависимости пакета",
    )
    parser.add_argument(
        "--filter",
        default="",
        help="Не учитывать пакеты, имя которых содержит подстроку",
    )
    parser.add_argument(
        "--order",
        action="store_true",
        help="Вывести порядок загрузки зависимостей",
    )
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Вывести все пользовательские параметры (режим этапа 1)",
    )


def build_parser() -> argparse.ArgumentParser:
    """Создать и настроить парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog="dependency-visualizer",
        description="Построение графа зависимостей Maven-пакетов.",
    )
    _add_package_arguments(parser)
    _add_output_arguments(parser)
    return parser


def _validate_package(parser, package: str, test_mode: bool) -> None:
    """Проверить формат имени тестовой вершины или Maven-координат."""
    if test_mode and not re.fullmatch(r"[A-Z]+", package):
        parser.error(
            "в тестовом режиме --package должен состоять "
            "из больших латинских букв"
        )
    if not test_mode and not COORDINATE_RE.fullmatch(package):
        parser.error(
            "--package должен иметь формат groupId:artifactId:version "
            "(например, org.slf4j:slf4j-api:2.0.13)"
        )


def _validate_repository(parser, repository: str, test_mode: bool) -> str:
    """Проверить путь к тестовому файлу или URL репозитория."""
    repository = repository.strip()
    if not repository:
        parser.error("--repository не может быть пустым")

    if test_mode:
        path = Path(repository).expanduser()
        if not path.is_file():
            parser.error(f"тестовый файл не найден: {path}")
        if path.suffix.lower() != ".json":
            parser.error("--test-mode ожидает JSON-файл с описанием графа")
        return str(path.resolve())

    parsed = urlsplit(repository)
    try:
        valid_port = parsed.port is None or 1 <= parsed.port <= 65535
    except ValueError:
        valid_port = False
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or not valid_port
        or parsed.username
        or parsed.password
    ):
        parser.error(
            "для реального режима --repository должен быть корректным "
            "HTTP(S)-URL без логина и пароля"
        )
    return repository.rstrip("/")


def parse_args(argv=None) -> Config:
    """Разобрать аргументы и вернуть конфигурацию приложения."""
    parser = build_parser()
    args = parser.parse_args(argv)
    _validate_package(parser, args.package, args.test_mode)
    repository = _validate_repository(
        parser, args.repository, args.test_mode
    )
    return Config(
        package=args.package,
        repository=repository,
        test_mode=args.test_mode,
        ascii_tree=args.ascii,
        direct_only=args.direct,
        filter_substring=args.filter,
        show_order=args.order,
        show_config=args.show_config,
    )


def print_config(config: Config) -> None:
    """Вывести параметры конфигурации в формате ключ-значение."""
    print(f"package={config.package}")
    print(f"repository={config.repository}")
    print(f"test_mode={config.test_mode}")
    print(f"ascii={config.ascii_tree}")
    print(f"direct={config.direct_only}")
    print(f"filter={config.filter_substring}")
    print(f"order={config.show_order}")
    print(f"show_config={config.show_config}")
