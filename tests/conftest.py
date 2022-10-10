import hashlib
import os
import sys
from pathlib import Path
from tempfile import mkdtemp
from unittest.mock import patch

import pytest


@pytest.fixture
def sha256sum():
    def _sha256sum(file_path: Path) -> str:
        sha = hashlib.sha256()
        with file_path.open("rb") as f:
            while True:
                block = f.read(1 << 16)
                if not block:
                    break
                sha.update(block)
        return sha.hexdigest()

    return _sha256sum


@pytest.fixture(scope="module")
def wheel_path():
    """
    Create a dummy python wheel
    """

    tmp_path = Path(mkdtemp())
    os.chdir(str(tmp_path))
    (tmp_path / "foobar").mkdir()

    open("foobar/test.py", "w").close()
    open("foobar/__init__.py", "w").close()

    with patch.object(sys, "argv", ["", "bdist_wheel"]):
        from setuptools import setup

        setup(
            name="foobar",
            author="John Doe",
            url="http://perdu.com",
            packages=["foobar"],
            install_requires=["py>=0.1"],
            entry_points={"console_scripts": ["wheel2deb=wheel2deb.cli:main"]},
            python_requires="!=3.0.*, !=3.1.*, !=3.2.*, <4",
            version="0.1.0",
        )

    return list(tmp_path.glob("dist/*.whl"))[0]
