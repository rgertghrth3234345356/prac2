"""Тесты чтения Maven POM XML."""

from src.repository_reader import MavenRepositoryReader


POM_XML = b"""\
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.example</groupId>
  <artifactId>sample</artifactId>
  <version>1.0</version>
  <properties>
    <dependency.version>2.5</dependency.version>
  </properties>
  <dependencyManagement>
    <dependencies>
      <dependency>
        <groupId>org.example</groupId>
        <artifactId>managed</artifactId>
        <version>${dependency.version}</version>
      </dependency>
    </dependencies>
  </dependencyManagement>
  <dependencies>
    <dependency>
      <groupId>org.example</groupId>
      <artifactId>managed</artifactId>
    </dependency>
    <dependency>
      <groupId>org.example</groupId>
      <artifactId>ignored</artifactId>
      <version>1.0</version>
      <scope>test</scope>
    </dependency>
  </dependencies>
</project>
"""


def test_reader_resolves_managed_dependency(monkeypatch):
    """Проверить чтение POM, подстановку свойств и dependencyManagement."""
    reader = MavenRepositoryReader("https://repo.example")
    monkeypatch.setattr(reader, "_download", lambda *args: POM_XML)

    pom = reader.read_pom("org.example", "sample", "1.0")

    assert len(pom.dependencies) == 1
    assert pom.dependencies[0].coordinates == "org.example:managed:2.5"


def test_reader_caches_pom(monkeypatch):
    """Проверить повторное использование уже загруженного POM."""
    reader = MavenRepositoryReader("https://repo.example")
    calls = []

    def download(*coordinates):
        """Записать вызов загрузки и вернуть тестовый XML."""
        calls.append(coordinates)
        return POM_XML

    monkeypatch.setattr(reader, "_download", download)
    reader.read_pom("org.example", "sample", "1.0")
    reader.read_pom("org.example", "sample", "1.0")

    assert len(calls) == 1


def test_coordinates_accept_classifier():
    """Проверить разбор Maven-координат с classifier."""
    assert MavenRepositoryReader._coordinates(
        "org.example:sample:1.0:tests"
    ) == ("org.example", "sample", "1.0")


def test_optional_dependency_is_preserved_in_pom_model(monkeypatch):
    """Optional остаётся прямой зависимостью текущего Maven-пакета."""
    optional_pom = b'''\
    <project xmlns="http://maven.apache.org/POM/4.0.0">
      <modelVersion>4.0.0</modelVersion>
      <groupId>org.example</groupId>
      <artifactId>sample</artifactId>
      <version>1.0</version>
      <dependencies>
        <dependency>
          <groupId>org.example</groupId>
          <artifactId>extra</artifactId>
          <version>2.0</version>
          <optional>true</optional>
        </dependency>
      </dependencies>
    </project>
    '''
    reader = MavenRepositoryReader("https://repo.example")
    monkeypatch.setattr(reader, "_download", lambda *args: optional_pom)

    dependencies = reader.direct_dependencies("org.example:sample:1.0")

    assert len(dependencies) == 1
    assert dependencies[0].coordinates == "org.example:extra:2.0"
    assert dependencies[0].optional is True
