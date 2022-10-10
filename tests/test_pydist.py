from wheel2deb.pydist import Entrypoint, parse_wheel
from wheel2deb.pyvers import Version


def test_metadata__should_return_correct_wheel_metadata_when_wheel_is_well_formed(
    wheel_path, tmp_path
):
    wheel = parse_wheel(wheel_path, tmp_path)
    assert wheel.metadata.author == "John Doe"
    assert wheel.metadata.home_page == "http://perdu.com"


def test_cpython_supported__should_return_true_when_cpython_is_supported_by_wheel(
    wheel_path,
    tmp_path,
):
    wheel = parse_wheel(wheel_path, tmp_path)
    assert wheel.cpython_supported is True


def test_requires__should_return_list_of_dependencies_for_wheel(
    wheel_path,
    tmp_path,
):
    wheel = parse_wheel(wheel_path, tmp_path)
    requirements = wheel.requires({"python_version": "3"})
    assert [r.name for r in requirements] == ["py"]


def test_version_supported__should_return_true_when_wheel_supports_python_version(
    wheel_path, tmp_path
):
    wheel = parse_wheel(wheel_path, tmp_path)
    assert wheel.version_supported(Version(3, 6)) is True
    assert wheel.version_supported(Version(3, 7)) is True
    assert wheel.version_supported(Version(3, 8)) is True


def test_version_supported__should_return_false_when_wheel_does_not_support_python_version(  # noqa: E501
    wheel_path, tmp_path
):
    wheel = parse_wheel(wheel_path, tmp_path)
    assert wheel.version_supported(Version(2)) is False
    assert wheel.version_supported(Version(3, 1)) is False


def test_entrypoints__should_return_list_of_entrypoints_when_wheel_has_entrypoints(
    wheel_path, tmp_path
):
    wheel = parse_wheel(wheel_path, tmp_path)
    assert wheel.entrypoints == [Entrypoint("wheel2deb", "wheel2deb.cli", "main")]
