import os
import sys
import pytest
from tempfile import mkdtemp
from pathlib import Path
from unittest.mock import patch


@pytest.fixture(scope="module")
def wheel_path():
    """
    Create a dummy python wheel
    """

    tmp_path = Path(mkdtemp())
    os.chdir(str(tmp_path))
    (tmp_path / 'foobar').mkdir()

    open('foobar/test.py', 'w').close()
    open('foobar/__init__.py', 'w').close()

    with patch.object(sys, 'argv', ['', 'bdist_wheel']):
        from setuptools import setup
        setup(name='foobar',
              author='John Doe',
              url='http://perdu.com',
              packages=['foobar'],
              install_requires=['py>=0.1'],
              entry_points={
                  'console_scripts': ['entrypoint=foobar.test:entrypoint']
              },
              python_requires='!=3.0.*, !=3.1.*, !=3.2.*, <4',
              version='0.1.0')

    path = list(tmp_path.glob('dist/*.whl'))[0]
    return path
