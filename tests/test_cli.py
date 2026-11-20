"""Проверки параметров командной строки и режима прямых зависимостей."""

import json

import pytest

from src.argument_parser import parse_args
from src.main import main


def test_parser_accepts_classifier_and_direct_mode():
    """Проверить дополнительные Maven-координаты и прямой режим."""
    config = parse_args(
        [
            "--package",
            "org.example:sample:1.0:tests",
            "--repository",
            "https://repo.example/maven2",
            "--direct",
        ]
    )
    assert config.direct_only is True


def test_parser_rejects_invalid_repository_url():
    """Проверить обработку некорректного URL репозитория."""
    with pytest.raises(SystemExit):
        parse_args(
            [
                "--package",
                "org.example:sample:1.0",
                "--repository",
                "not-a-url",
            ]
        )


def test_main_direct_test_mode(tmp_path, capsys):
    """Проверить вывод прямых зависимостей из тестового репозитория."""
    graph_file = tmp_path / "graph.json"
    graph_file.write_text(
        json.dumps({"A": ["B", "C"], "B": [], "C": []}),
        encoding="utf-8",
    )

    result = main(
        [
            "--package",
            "A",
            "--repository",
            str(graph_file),
            "--test-mode",
            "--direct",
        ]
    )

    output = capsys.readouterr().out
    assert result == 0
    assert "- B" in output
    assert "- C" in output
    assert "Mermaid" not in output
