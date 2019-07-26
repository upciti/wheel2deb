import pytest
import sys
import os
import hashlib
from unittest.mock import patch
from tempfile import TemporaryDirectory

import wheel2deb
from wheel2deb import parse_args
from _wheel2deb.context import load


def digests(fname):
    sha = hashlib.sha256()
    with open(str(fname), 'rb') as f:
        while True:
            block = f.read(1 << 16)
            if not block:
                break
            sha.update(block)

    return sha.hexdigest()


def test_parse_args():
    args = ['--map', 'attrs=attr', '--python-version', '1']
    parser = parse_args(args)
    assert parser.map['attrs'] == 'attr'
    assert parser.python_version == '1'


def test_load_config_file(tmp_path):
    config_path = tmp_path / 'foo.yml'
    with open(str(config_path), 'w') as f:
        f.write('.+:\n'
                '  version_template: "1.0.0"\n'
                '  map:\n'
                '    attrs: attr\n'
                '  depends:\n'
                '    - python-foobar\n')

    args = ['--config', str(config_path)]
    parser = parse_args(args)
    settings = load(parser.config)

    assert settings.get_ctx('foo').map['attrs'] == 'attr'
    assert settings.get_ctx('foo').depends[0] == 'python-foobar'


@patch('sys.argv', ['wheel2deb', '-h'])
def test_help():
    """ Test wheel2deb -h """

    with TemporaryDirectory() as directory:
        os.chdir(directory)
        with pytest.raises(SystemExit) as e:
            wheel2deb.main()
            assert e.code == 0


def test_conversion(tmp_path, wheel_path):
    """ Test the conversion of a dummy wheel foobar """

    os.chdir(str(tmp_path))

    # convert wheel to debian source package
    with patch.object(sys, 'argv', ['', '-x', str(wheel_path.parent)]):
        with patch.object(wheel2deb.sys, "exit") as mock_exit:
            wheel2deb.main()
            assert mock_exit.call_args[0][0] == 0

    unpack_path = tmp_path / 'output/foobar-0.1.0-py3-none-any'
    assert unpack_path.exists()

    # build source package
    with patch.object(sys, 'argv', ['', 'build']):
        with patch.object(wheel2deb.sys, "exit") as mock_exit:
            wheel2deb.main()
            assert mock_exit.call_args[0][0] == 0

    # output dir should contain a .deb
    package_list = list((tmp_path / 'output').glob('*.deb'))
    assert package_list

    package_path = package_list[0]
    assert package_path.name.startswith('python3-foobar_0.1.0-1')

    package_hash = digests(package_list[0])

    # check that the entrypoint will be installed in /usr/bin
    assert (unpack_path / 'debian/python3-foobar/usr/bin/entrypoint').exists()

    # idempotence: delete package, rerun build command
    # and check  that both packages have the same hash
    package_list[0].unlink()
    with patch.object(sys, 'argv', ['', 'build']):
        with patch.object(wheel2deb.sys, "exit") as mock_exit:
            wheel2deb.main()
            assert mock_exit.call_args[0][0] == 0
    assert digests(package_path) == package_hash


def test_build(tmp_path):
    os.chdir(str(tmp_path))
    os.mkdir('output')

    with patch.object(sys, 'argv', ['', 'build', '-f', '-j1']):
        with pytest.raises(SystemExit) as e:
            wheel2deb.main()
            assert e.code == 0
