import pytest

from _wheel2deb.pyvers import Version, VersionRange


def test_python_version():
    v2 = Version.from_str("2")
    v36 = Version.from_str("3.6")
    v37 = v36.inc()

    assert v2.minor == 0
    assert v36.major == 3 and v36.minor == 6
    assert str(v36) == "3.6"
    assert str(v2) == "2.0"
    assert v37 > v36 > v2


def test_python_version_interval():
    v34 = Version.from_str("3.4")
    v35 = Version.from_str("3.5")
    v36 = Version.from_str("3.6")

    v35v36 = VersionRange(v35, v36)
    v35p = VersionRange(v35, None)
    vall = VersionRange(None, None)

    with pytest.raises(ValueError):
        VersionRange(v34, v34)

    with pytest.raises(ValueError):
        VersionRange(v35, v34)

    assert v36 not in v35v36
    assert v35 in v35v36
    assert v35 in v35p
    assert v34 not in v35p
    assert v34 in vall
