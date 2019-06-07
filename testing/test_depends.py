from _wheel2deb.depends import suggest_name, search_python_deps
from _wheel2deb.context import Context
from _wheel2deb.pyvers import Version
from _wheel2deb.pydist import Wheel


def test_name_suggestion():
    ctx = Context()
    assert suggest_name(ctx, 'Click') == 'python3-click'
    assert suggest_name(
        ctx, 'opencv-python-headless') == 'python3-opencv-headless'

    assert suggest_name(ctx, 'O_O') == 'python3-o-o'

    ctx.python_version = Version(2)
    assert suggest_name(ctx, 'Click') == 'python-click'


def test_search_python_deps(wheel_path):
    ctx = Context()
    wheel = Wheel(wheel_path)
    deps, missing_deps = search_python_deps(ctx, wheel)

    assert deps[0].startswith('python3-somepackage (>= 5.0')
    assert missing_deps[0] == 'somepackage>=5.0'
