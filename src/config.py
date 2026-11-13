"""Конфигурация CLI-приложения."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Параметры запуска приложения."""

    package: str
    repository: str
    test_mode: bool = False
    ascii_tree: bool = False
    filter_substring: str = ""
    show_order: bool = False
    show_config: bool = False
