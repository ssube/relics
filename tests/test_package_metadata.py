from importlib import metadata
from pathlib import Path

import relics


def test_runtime_version_uses_distribution_metadata() -> None:
    assert relics.__version__ == metadata.version("relics-ecs")


def test_package_is_marked_typed() -> None:
    assert Path(relics.__file__).with_name("py.typed").is_file()
