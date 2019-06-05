import pytest
import sys
import os
from unittest.mock import patch
from tempfile import TemporaryDirectory

import wheel2deb
from wheel2deb import parse_args


def test_parse_args():
    args = ['--map', 'attrs=attr', '--python-version', '1']
    parser = parse_args(args)
    assert parser.map['attrs'] == 'attr'
    assert parser.python_version == '1'


@patch('sys.argv', ['wheel2deb', '-h'])
def test_help():
    """ Test wheel2deb -h """

    with TemporaryDirectory() as directory:
        os.chdir(directory)
        with pytest.raises(SystemExit) as e:
            wheel2deb.main()
            assert e.code == 0


def test_conversion(tmp_path):
    """ Test the conversion of a dummy wheel foobar """

    os.chdir(str(tmp_path))
    (tmp_path / 'foobar').mkdir()

    with open('foobar/__init__.py', 'w') as f:
        f.write('')

    with open('foobar/test.py', 'w') as f:
        f.write('print("Hello world !")')

    # create dummy wheel
    with patch.object(sys, 'argv', ['', 'bdist_wheel']):
        from setuptools import setup
        setup(name='foobar',
              author='John Doe',
              packages=['foobar'],
              version='0.1.0')

    # convert wheel to debian source package
    with patch.object(sys, 'argv', ['', '-x', 'dist']):
        with pytest.raises(SystemExit) as e:
            wheel2deb.main()
            assert e.code == 0

    assert (tmp_path / 'output/foobar-0.1.0-py3-none-any').exists()

    # build source package
    with patch.object(sys, 'argv', ['', 'build']):
        with pytest.raises(SystemExit) as e:
            wheel2deb.main()
            assert e.code == 0

    # output dir should contain a .deb
    package_list = list((tmp_path / 'output').glob('*.deb'))
    assert package_list

    assert package_list[0].name.startswith('python3-foobar_0.1.0-1')
