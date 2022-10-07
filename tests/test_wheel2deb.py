import os

import pytest
from typer.testing import CliRunner

from wheel2deb.cli import app

valid_configuration = """\
.+:
  map:
    attrs: attr
  depends:
    - python-foobar
"""


@pytest.fixture
def call_wheel2deb(tmp_path):
    def _invoke(*args, conf: str | None = None):
        runner = CliRunner()
        configuration_path = tmp_path / "wheel2deb.yml"
        if conf is not None:
            configuration_path.write_text(conf)
        os.environ.update(
            {
                "WHEEL2DEB_VERBOSE": "1",
                "WHEEL2DEB_OUTPUT_DIR": str(tmp_path / "output"),
                "WHEEL2DEB_CONFIG": str(configuration_path),
            }
        )
        args = [str(arg) for arg in args]
        return runner.invoke(app, args, catch_exceptions=False)

    return _invoke


def test_convert(tmp_path, wheel_path, call_wheel2deb):
    result = call_wheel2deb("convert", "-x", wheel_path.parent, conf=valid_configuration)
    assert result.exit_code == 0
    source_package_path = tmp_path / "output/python3-foobar_0.1.0-1~w2d0_all"
    assert source_package_path.exists()
    entrypoint = source_package_path / "entrypoints/entrypoint"
    assert entrypoint.exists()
    shebang = list(entrypoint.read_text().splitlines())[0]
    assert shebang == "#!/usr/bin/python3"


def test_build(tmp_path, wheel_path, sha256sum, call_wheel2deb):
    call_wheel2deb("convert", "-x", wheel_path.parent, conf=valid_configuration)
    result = call_wheel2deb("build")
    assert result.exit_code == 0
    assert (tmp_path / "output/python3-foobar_0.1.0-1~w2d0_all.deb").is_file()


def test_build_idempotence(tmp_path, wheel_path, sha256sum, call_wheel2deb):
    call_wheel2deb("convert", "-x", wheel_path.parent, conf=valid_configuration)
    call_wheel2deb("build")
    package_path = tmp_path / "output/python3-foobar_0.1.0-1~w2d0_all.deb"
    checksum = sha256sum(package_path)
    package_path.unlink()
    call_wheel2deb("build")
    assert checksum == sha256sum(package_path)


def test_default(tmp_path, wheel_path, sha256sum, call_wheel2deb):
    result = call_wheel2deb("-x", wheel_path.parent, conf=valid_configuration)
    assert result.exit_code == 0
    assert (tmp_path / "output/python3-foobar_0.1.0-1~w2d0_all.deb").is_file()
