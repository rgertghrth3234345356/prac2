"""Чтение POM-файлов Maven без использования менеджера пакетов."""

from __future__ import annotations

import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

from .package_info import PackageInfo, PomInfo

MAVEN_COORDINATE_PARTS = 3
MAX_INTERPOLATION_PASSES = 10
EXCLUDED_SCOPES = {"test", "provided", "system", "import"}


class RepositoryError(RuntimeError):
    """Ошибка загрузки или разбора метаданных Maven."""


class MavenRepositoryReader:
    """Загружает и разбирает POM-файлы из Maven-репозитория."""

    def __init__(self, base_url: str, timeout: int = 20):
        """Создать читатель для указанного Maven-репозитория."""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._pom_cache: dict[tuple[str, str, str], PomInfo] = {}

    @staticmethod
    def _coordinates(value: str) -> tuple[str, str, str]:
        """Разделить координаты Maven на три обязательные части."""
        parts = value.split(":")
        if len(parts) != MAVEN_COORDINATE_PARTS:
            raise ValueError(
                "Ожидаются координаты groupId:artifactId:version"
            )
        return parts[0], parts[1], parts[2]

    def _download(
        self,
        group_id: str,
        artifact_id: str,
        version: str,
    ) -> bytes:
        """Загрузить POM-файл по Maven-координатам."""
        path = "/".join(
            group_id.split(".")
            + [artifact_id, version, f"{artifact_id}-{version}.pom"]
        )
        url = f"{self.base_url}/{path}"
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "DependencyVisualizer/1.0"},
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
            ) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RepositoryError(
                f"Не удалось загрузить POM {url}: {exc}"
            ) from exc

    @staticmethod
    def _namespace(root: ET.Element) -> str:
        """Вернуть XML-пространство имён корневого POM-элемента."""
        if root.tag.startswith("{"):
            return root.tag.split("}", 1)[0] + "}"
        return ""

    @staticmethod
    def _find(parent, name: str, namespace: str):
        """Найти дочерний XML-элемент с учётом namespace."""
        if parent is None:
            return None
        return parent.find(f"{namespace}{name}")

    @classmethod
    def _value(
        cls,
        parent,
        name: str,
        namespace: str,
        default: str = "",
    ) -> str:
        """Получить текст дочернего элемента или значение по умолчанию."""
        node = cls._find(parent, name, namespace)
        if node is None:
            return default
        return (node.text or "").strip()

    @classmethod
    def _read_properties(
        cls,
        root: ET.Element,
        namespace: str,
        fallback: tuple[str, str, str],
    ) -> tuple[str, str, str, dict[str, str]]:
        """Извлечь координаты проекта и свойства POM."""
        group_id, artifact_id, version = fallback
        parent = cls._find(root, "parent", namespace)
        parent_group = cls._value(parent, "groupId", namespace)
        parent_version = cls._value(parent, "version", namespace)
        group = cls._value(
            root, "groupId", namespace, parent_group or group_id
        )
        artifact = cls._value(root, "artifactId", namespace, artifact_id)
        pom_version = cls._value(
            root, "version", namespace, parent_version or version
        )

        properties = {}
        properties_node = cls._find(root, "properties", namespace)
        if properties_node is not None:
            for child in list(properties_node):
                name = child.tag.split("}", 1)[-1]
                properties[name] = (child.text or "").strip()

        properties.update({
            "project.groupId": group,
            "pom.groupId": group,
            "project.artifactId": artifact,
            "pom.artifactId": artifact,
            "project.version": pom_version,
            "pom.version": pom_version,
        })
        return group, artifact, pom_version, properties

    @staticmethod
    def _interpolate(value: str, properties: dict[str, str]) -> str:
        """Подставить значения свойств Maven в строку POM."""
        pattern = re.compile(r"\$\{([^}]+)\}")
        for _ in range(MAX_INTERPOLATION_PASSES):
            updated = pattern.sub(
                lambda match: properties.get(
                    match.group(1), match.group(0)
                ),
                value,
            )
            if updated == value:
                break
            value = updated
        return value

    @classmethod
    def _read_management(
        cls,
        root: ET.Element,
        namespace: str,
        properties: dict[str, str],
    ) -> dict[tuple[str, str], str]:
        """Извлечь версии из секции dependencyManagement."""
        management = {}
        management_node = cls._find(root, "dependencyManagement", namespace)
        dependencies = cls._find(management_node, "dependencies", namespace)
        if dependencies is None:
            return management

        for element in list(dependencies):
            if element.tag.split("}", 1)[-1] != "dependency":
                continue
            group = cls._dependency_value(
                element, "groupId", namespace, properties
            )
            artifact = cls._dependency_value(
                element, "artifactId", namespace, properties
            )
            version = cls._dependency_value(
                element, "version", namespace, properties
            )
            if group and artifact and version:
                management[(group, artifact)] = version
        return management

    @classmethod
    def _dependency_value(
        cls,
        element: ET.Element,
        name: str,
        namespace: str,
        properties: dict[str, str],
        default: str = "",
    ) -> str:
        """Получить и интерполировать поле Maven-зависимости."""
        value = cls._value(element, name, namespace, default)
        return cls._interpolate(value, properties)

    @classmethod
    def _parse_dependency(
        cls,
        element: ET.Element,
        namespace: str,
        properties: dict[str, str],
        management: dict[tuple[str, str], str],
    ) -> PackageInfo | None:
        """Преобразовать XML-элемент зависимости в PackageInfo."""
        group = cls._dependency_value(
            element, "groupId", namespace, properties
        )
        artifact = cls._dependency_value(
            element, "artifactId", namespace, properties
        )
        version = cls._dependency_value(
            element, "version", namespace, properties
        )
        scope = cls._dependency_value(
            element, "scope", namespace, properties, "compile"
        ) or "compile"
        optional = cls._dependency_value(
            element, "optional", namespace, properties, "false"
        ).lower() == "true"
        classifier = cls._dependency_value(
            element, "classifier", namespace, properties
        )

        if not version:
            version = management.get((group, artifact), "")
        if not group or not artifact or not version or optional:
            return None
        if scope in EXCLUDED_SCOPES:
            return None
        return PackageInfo(group, artifact, version, scope, classifier)

    @classmethod
    def _read_dependencies(
        cls,
        root: ET.Element,
        namespace: str,
        properties: dict[str, str],
        management: dict[tuple[str, str], str],
    ) -> list[PackageInfo]:
        """Извлечь обычные зависимости из секции dependencies."""
        node = cls._find(root, "dependencies", namespace)
        if node is None:
            return []

        dependencies = []
        for element in list(node):
            if element.tag.split("}", 1)[-1] != "dependency":
                continue
            dependency = cls._parse_dependency(
                element, namespace, properties, management
            )
            if dependency is not None:
                dependencies.append(dependency)
        return dependencies

    def read_pom(
        self,
        group_id: str,
        artifact_id: str,
        version: str,
    ) -> PomInfo:
        """Загрузить POM и извлечь метаданные и прямые зависимости."""
        key = (group_id, artifact_id, version)
        if key in self._pom_cache:
            return self._pom_cache[key]

        raw = self._download(*key)
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            coordinates = ":".join(key)
            raise RepositoryError(
                f"Некорректный XML POM для {coordinates}: {exc}"
            ) from exc

        namespace = self._namespace(root)
        group, artifact, pom_version, properties = self._read_properties(
            root, namespace, key
        )
        management = self._read_management(
            root, namespace, properties
        )
        dependencies = self._read_dependencies(
            root, namespace, properties, management
        )
        info = PomInfo(
            group, artifact, pom_version, properties, management, dependencies
        )
        self._pom_cache[key] = info
        return info

    def direct_dependencies(self, coordinates: str) -> list[PackageInfo]:
        """Вернуть прямые зависимости по координатам Maven."""
        return self.read_pom(*self._coordinates(coordinates)).dependencies
