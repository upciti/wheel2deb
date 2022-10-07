from wheel2deb.context import Context
from wheel2deb.depends import get_dependency_string, search_python_deps, suggest_name
from wheel2deb.pydist import Wheel
from wheel2deb.pyvers import Version


def test_name_suggestion():
    ctx = Context()
    assert suggest_name(ctx, "Click") == "python3-click"
    assert suggest_name(ctx, "opencv-python-headless") == "python3-opencv-headless"

    assert suggest_name(ctx, "O_O") == "python3-o-o"

    ctx.python_version = Version(2)
    assert suggest_name(ctx, "Click") == "python-click"


def test_search_python_deps(wheel_path):
    ctx = Context()
    wheel = Wheel(wheel_path)
    deps, missing_deps = search_python_deps(ctx, wheel)

    assert deps[0].startswith("python3-py (>= 0.1")
    assert not missing_deps


def test_get_dependency_string():
    assert get_dependency_string("python3-py", "==", "1.2.3") == "python3-py (<< 1.3)"
    assert get_dependency_string("python3-py", "==", "1.2.*") == "python3-py (<< 1.3)"
    assert get_dependency_string("python3-py", "==", "1.2") == "python3-py (<< 1.3)"
    assert get_dependency_string("python3-py", "==", "1.*") == "python3-py (<< 2)"
    assert get_dependency_string("python3-py", "==", "1") == "python3-py (<< 2)"

    assert get_dependency_string("python3-py", ">=", "1.2.3") == "python3-py (>= 1.2.3)"
    assert get_dependency_string("python3-py", ">=", "1.2.*") == "python3-py (>= 1.2)"
    assert get_dependency_string("python3-py", ">=", "1.2") == "python3-py (>= 1.2)"
    assert get_dependency_string("python3-py", ">=", "1.*") == "python3-py (>= 1)"
    assert get_dependency_string("python3-py", ">=", "1") == "python3-py (>= 1)"

    assert get_dependency_string("python3-py", "<=", "1.2.3") == "python3-py (<= 1.2.3-+)"
    assert get_dependency_string("python3-py", "<=", "1.2.*") == "python3-py (<= 1.2-+)"
    assert get_dependency_string("python3-py", "<=", "1.2") == "python3-py (<= 1.2-+)"
    assert get_dependency_string("python3-py", "<=", "1.*") == "python3-py (<= 1-+)"
    assert get_dependency_string("python3-py", "<=", "1") == "python3-py (<= 1-+)"
