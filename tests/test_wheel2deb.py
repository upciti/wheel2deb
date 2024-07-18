import os
import shutil

import pytest
from typer.testing import CliRunner

from wheel2deb.cli import app
from wheel2deb.pydist import EXTRACT_PATH

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
        if EXTRACT_PATH.exists():
            shutil.rmtree(EXTRACT_PATH)
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


def test_convert__should_install_entrypoints_in_usr_bin_directory_with_the_right_shebang_when_wheel_has_entrypoints(  # noqa: E501
    tmp_path,
    wheel_path,
    call_wheel2deb,
):
    result = call_wheel2deb("convert", "-x", wheel_path.parent, conf=valid_configuration)
    assert result.exit_code == 0
    source_package_path = tmp_path / "output/python3-foobar_0.1.0-1~w2d0_all"
    assert source_package_path.exists() is True
    entrypoint = source_package_path / "entrypoints/wheel2deb"
    assert entrypoint.exists() is True
    shebang = next(iter(entrypoint.read_text().splitlines()))
    assert shebang == "#!/usr/bin/python3"


def test_build__should_produce_a_debian_pacakge_when_configuration_is_valid(
    tmp_path, wheel_path, sha256sum, call_wheel2deb
):
    call_wheel2deb("convert", "-x", wheel_path.parent, conf=valid_configuration)
    result = call_wheel2deb("build")
    assert result.exit_code == 0
    assert (tmp_path / "output/python3-foobar_0.1.0-1~w2d0_all.deb").is_file()


def test_build__should_produce_identical_debian_packages_when_run_twice_with_same_conf_and_wheel(  # noqa: E501
    tmp_path, wheel_path, sha256sum, call_wheel2deb
):
    call_wheel2deb("convert", "-x", wheel_path.parent, conf=valid_configuration)
    call_wheel2deb("build")
    package_path = tmp_path / "output/python3-foobar_0.1.0-1~w2d0_all.deb"
    checksum = sha256sum(package_path)
    package_path.unlink()
    call_wheel2deb("build")
    assert checksum == sha256sum(package_path)


def test_default__should_convert_wheel_and_build_debian_package_when_conf_is_valid(
    tmp_path, wheel_path, sha256sum, call_wheel2deb
):
    result = call_wheel2deb("-x", wheel_path.parent, conf=valid_configuration)
    assert result.exit_code == 0
    assert (tmp_path / "output/python3-foobar_0.1.0-1~w2d0_all.deb").is_file()
