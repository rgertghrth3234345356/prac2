"""Модели Maven-пакета и его зависимостей."""

from dataclasses import dataclass, field


@dataclass(frozen=True, order=True)
class PackageInfo:
    """Координаты и параметры Maven-зависимости."""

    group_id: str
    artifact_id: str
    version: str
    scope: str = "compile"
    classifier: str = ""
    optional: bool = False

    @property
    def coordinates(self) -> str:
        """Вернуть координаты пакета в формате Maven."""
        base = f"{self.group_id}:{self.artifact_id}:{self.version}"
        if self.classifier:
            return f"{base}:{self.classifier}"
        return base


@dataclass
class PomInfo:
    """Метаданные проекта, извлечённые из pom.xml."""

    group_id: str
    artifact_id: str
    version: str
    properties: dict[str, str] = field(default_factory=dict)
    dependency_management: dict[tuple[str, str], str] = field(
        default_factory=dict
    )
    dependencies: list[PackageInfo] = field(default_factory=list)
