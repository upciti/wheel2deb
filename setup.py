from setuptools import setup

with open('src/_wheel2deb/version.py') as f:
    exec(f.read())

INSTALL_REQUIRES = [
    'setuptools',
    'wheel',
    'pkginfo',
    'jinja2',
    'colorama',
    'attrs>=17',
    'packaging',
    'pyyaml'
]

setup(setup_requires=['setuptools>=38.6.0'],
      package_dir={'': 'src'},
      install_requires=INSTALL_REQUIRES,
      include_package_data=True,
      version=__version__)
