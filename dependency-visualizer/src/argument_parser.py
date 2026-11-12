"""Разбор и проверка аргументов командной строки."""

import argparse
import re
from pathlib import Path

from .config import Config


COORDINATE_RE = re.compile(
    r"^[A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+:[A-Za-z0-9_.+-]+$"
)


def build_parser() -> argparse.ArgumentParser:
    """Создать и настроить парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog="dependency-visualizer",
        description="Построение графа зависимостей Maven-пакетов.",
    )
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
    parser.add_argument(
        "--ascii",
        action="store_true",
        help="Вывести зависимости в виде ASCII-дерева",
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
    return parser


def parse_args(argv=None) -> Config:
    """Разобрать аргументы и вернуть конфигурацию приложения."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.test_mode:
        if not re.fullmatch(r"[A-Z]+", args.package):
            parser.error(
                "в тестовом режиме --package должен состоять "
                "из больших латинских букв"
            )
    elif not COORDINATE_RE.fullmatch(args.package):
        parser.error(
            "--package должен иметь формат groupId:artifactId:version "
            "(например, org.slf4j:slf4j-api:2.0.13)"
        )

    repository = args.repository.strip()
    if not repository:
        parser.error("--repository не может быть пустым")

    if args.test_mode:
        path = Path(repository).expanduser()
        if not path.is_file():
            parser.error(f"тестовый файл не найден: {path}")
        if path.suffix.lower() != ".json":
            parser.error("--test-mode ожидает JSON-файл с описанием графа")
        repository = str(path.resolve())
    elif not (
        repository.startswith("https://")
        or repository.startswith("http://")
    ):
        parser.error(
            "для реального режима --repository должен быть HTTP(S)-URL"
        )

    return Config(
        package=args.package,
        repository=(
            repository if args.test_mode else repository.rstrip("/")
        ),
        test_mode=args.test_mode,
        ascii_tree=args.ascii,
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
    print(f"filter={config.filter_substring}")
    print(f"order={config.show_order}")
    print(f"show_config={config.show_config}")
