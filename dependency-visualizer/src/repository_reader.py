"""Чтение POM-файлов Maven без использования менеджера пакетов."""

from __future__ import annotations

import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

from .package_info import PackageInfo, PomInfo


class RepositoryError(RuntimeError):
    """Ошибка загрузки или разбора метаданных Maven."""


class MavenRepositoryReader:
    """Загружает и разбирает POM-файлы из Maven-репозитория."""

    def __init__(self, base_url: str, timeout: int = 20):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._pom_cache: dict[tuple[str, str, str], PomInfo] = {}

    @staticmethod
    def _text(parent, tag: str, default: str = "") -> str:
        """Получить текст дочернего XML-элемента."""
        if parent is None:
            return default
        node = parent.find(tag)
        return (node.text or "").strip() if node is not None else default

    @staticmethod
    def _coordinates(value: str) -> tuple[str, str, str]:
        """Разделить Maven-координаты на groupId, artifactId и version."""
        parts = value.split(":")
        if len(parts) != 3:
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

    def read_pom(
        self,
        group_id: str,
        artifact_id: str,
        version: str,
    ) -> PomInfo:
        """Загрузить POM и извлечь из него метаданные и зависимости."""
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

        # Maven POM обычно использует namespace. Локальные имена
        # упрощают XPath.
        namespace = ""
        if root.tag.startswith("{"):
            namespace = root.tag.split("}", 1)[0] + "}"

        def find(parent, name):
            if parent is None:
                return None
            return parent.find(f"{namespace}{name}")

        def value(parent, name, default=""):
            node = find(parent, name)
            if node is None:
                return default
            return (node.text or "").strip()

        parent = find(root, "parent")
        parent_group = value(parent, "groupId")
        parent_version = value(parent, "version")

        group = value(root, "groupId", parent_group or group_id)
        artifact = value(root, "artifactId", artifact_id)
        pom_version = value(root, "version", parent_version or version)

        properties = {}
        properties_node = find(root, "properties")
        if properties_node is not None:
            for child in list(properties_node):
                name = child.tag.split("}", 1)[-1]
                properties[name] = (child.text or "").strip()

        properties.update(
            {
                "project.groupId": group,
                "pom.groupId": group,
                "project.artifactId": artifact,
                "pom.artifactId": artifact,
                "project.version": pom_version,
                "pom.version": pom_version,
            }
        )

        def interpolate(text: str) -> str:
            pattern = re.compile(r"\$\{([^}]+)\}")
            for _ in range(10):
                updated = pattern.sub(
                    lambda match: properties.get(
                        match.group(1),
                        match.group(0),
                    ),
                    text,
                )
                if updated == text:
                    break
                text = updated
            return text

        management = {}
        management_node = find(
            find(root, "dependencyManagement"),
            "dependencies",
        )
        if management_node is not None:
            for dependency in list(management_node):
                if dependency.tag.split("}", 1)[-1] != "dependency":
                    continue

                dep_group = interpolate(value(dependency, "groupId"))
                dep_artifact = interpolate(value(dependency, "artifactId"))
                dep_version = interpolate(value(dependency, "version"))

                if dep_group and dep_artifact and dep_version:
                    management[(dep_group, dep_artifact)] = dep_version

        dependencies = []
        dependencies_node = find(root, "dependencies")
        if dependencies_node is not None:
            for dependency in list(dependencies_node):
                if dependency.tag.split("}", 1)[-1] != "dependency":
                    continue

                dep_group = interpolate(value(dependency, "groupId"))
                dep_artifact = interpolate(value(dependency, "artifactId"))
                dep_version = interpolate(value(dependency, "version"))
                scope = interpolate(
                    value(dependency, "scope", "compile")
                ) or "compile"
                optional = (
                    interpolate(value(dependency, "optional", "false"))
                    .lower()
                    == "true"
                )
                classifier = interpolate(value(dependency, "classifier"))

                if not dep_version:
                    dep_version = management.get(
                        (dep_group, dep_artifact),
                        "",
                    )

                if not dep_group or not dep_artifact or not dep_version:
                    continue
                if optional:
                    continue
                if scope in {"test", "provided", "system", "import"}:
                    continue

                dependencies.append(
                    PackageInfo(
                        dep_group,
                        dep_artifact,
                        dep_version,
                        scope,
                        classifier,
                    )
                )

        info = PomInfo(
            group,
            artifact,
            pom_version,
            properties,
            management,
            dependencies,
        )
        self._pom_cache[key] = info
        return info

    def direct_dependencies(self, coordinates: str) -> list[PackageInfo]:
        """Вернуть прямые зависимости пакета по его Maven-координатам."""
        return self.read_pom(*self._coordinates(coordinates)).dependencies
