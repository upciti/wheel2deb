from _wheel2deb.depends import suggest_name
from _wheel2deb.context import Context
from _wheel2deb.pyvers import Version


def test_name_conversion():
    ctx = Context()
    assert suggest_name(ctx, 'Click') == 'python3-click'
    assert suggest_name(
        ctx, 'opencv-python-headless') == 'python3-opencv-headless'

    assert suggest_name(ctx, 'O_O') == 'python3-o-o'

    ctx.python_version = Version(2)
    assert suggest_name(ctx, 'Click') == 'python-click'
