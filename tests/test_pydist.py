from wheel2deb.pydist import Wheel
from wheel2deb.pyvers import Version


def test_parse_wheel(wheel_path):
    wheel = Wheel(wheel_path)

    assert wheel.requires({"python_version": "3"})[0].name == "py"

    assert wheel.metadata.author == "John Doe"
    assert wheel.metadata.home_page == "http://perdu.com"

    # test cpython support
    assert wheel.cpython_supported

    # test supported python version
    assert not wheel.version_supported(Version(2))
    assert not wheel.version_supported(Version(3, 1))
    assert wheel.version_supported(Version(3, 6))
