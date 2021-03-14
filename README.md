## wheel2deb: python wheel to debian package converter

[![Build Status](https://travis-ci.org/parkoview/wheel2deb.svg?branch=master)](https://travis-ci.org/parkoview/wheel2deb)
[![Coverage Status](https://coveralls.io/repos/github/parkoview/wheel2deb/badge.svg?branch=master)](https://coveralls.io/github/parkoview/wheel2deb?branch=master)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/581a27ffb7cc4907b52e27430abdc26d)](https://www.codacy.com/app/simon-parkoview/wheel2deb?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=parkoview/wheel2deb&amp;utm_campaign=Badge_Grade)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![PyPI version shields.io](https://img.shields.io/pypi/v/wheel2deb.svg)](https://pypi.python.org/pypi/wheel2deb/)
[![Downloads](https://static.pepy.tech/personalized-badge/wheel2deb?period=total&units=international_system&left_color=blue&right_color=green&left_text=Downloads)](https://pepy.tech/project/wheel2deb)

wheel2deb basically takes a list of wheels as input and produces a list of debian binary CPython packages (those prefixed with python- or python3-).

[![asciicast](https://asciinema.org/a/249779.svg)](https://asciinema.org/a/249779)

## Quick Example

The following shows how to convert numpy and pytest, along with their dependencies into a list of debian packages:

```sh
# Download (and build if needed) pytest, numpy and their requirements
pip3 wheel pytest numpy
# Convert all wheels to debian source packages
wheel2deb --map attrs=attr
# Call dpkg-buildpackages for each source package
wheel2deb build
ls -l output/*.deb
# Install generated packages
dpkg -i output/*.deb
# Run pytest on numpy
python3 -c "import numpy; numpy.test()"
```

## Project scope

-   Python 2.7 and 3
-   CPython only for now
-   support for non pure python wheels
-   support debian architectures all, armhf, amd64, i686
-   tested on jessie, stretch, buster so far, ubuntu should also work

## Requirements

`wheel2deb` uses python3-apt to search for debian packages, dpkg-shlibdeps to calculate shared library dependencies and apt-file to search packages providing shared library dependencies. `wheel2deb build` requires the usual tools to build a debian package:
```sh
apt update
apt install python3-apt apt-file dpkg-dev fakeroot build-essential devscripts debhelper
apt-file update
```

If you want to cross build packages for ARM, you will also need to install `binutils-arm-linux-gnueabihf`.

Converting pure python wheels, don't actually requires apt-file and dpkg-dev.

Keep in mind that you should only convert wheels that have been built for your distribution and architecture. wheel2deb will not warn you about ABI compatibility issues.

## Installation

wheel2deb is available from [pypi](https://pypi.org/project/wheel2deb/):

`pip install wheel2deb`

Docker images for jessie, stretch and buster are also available from the [docker hub](https://cloud.docker.com/u/parkoview/repository/docker/parkoview/wheel2deb):
 
`docker run -ti -v $(pwd):/data wheel2deb:stretch`

## Features

-   guess debian package names from wheel names and search for them in the cache
-   search packages providing shared library dependencies for wheels with native code
-   handle entrypoints and scripts (those will be installed in /usr/bin with a proper shebang)
-   try to locate licence files and to generate a debian/copyright file

## Options

Use `wheel2deb --help` and `wheel2deb build --help` to check all supported options

| Option                    | Description                                                                                         |
| ------------------------- | --------------------------------------------------------------------------------------------------- |
| -v                        | Enable debug logs.                                                                                  |
| -x                        | List of search paths where to look for python wheels. Defaults to current directory. Not recursive. |
| -o                        | Output directory where debian source packages will be produced. Defaults to ./output                |
| -i                        | List of wheel names to convert. By default all found wheels are included.                           |
| --python-version          | cpython version on the target debian distribution. Defaults to platform version (example: 3.4).     |
| --map                     | list of string pairs to explicitely map python dist names to debian package names. For instance: "--map foo:bar attrs:attr" will tell wheel2deb to map foo to python-bar and attrs to python-attr. |
| --depends                 | List of additional debian dependencies.                                                             |
| --epoch                   | Debian package epoch. Defaults to 0.                                                                |
| --revision                | Debian package revision. Defaults to 1.                                                             |
| --ignore-entry-points     | Don't include the wheel entrypoints in the debian package.                                          |
| --ignore-upstream-version | Ignore version specifiers from wheel requirements. For instance, if foo requires bar>=3.0.0, using this option will produce a debian package simply depending on bar instead of "bar (>= 3.0.0)". |

## Bugs/Requests

Please use the [GitHub issue tracker](<https://github.com/parkoview/wheel2deb/issues>) to submit bugs or request features.

## License

Copyright Parkoview SA 2019-2021.

Distributed under the terms of the [MIT](https://github.com/parkoview/wheel2deb/blob/master/LICENSE) license, wheel2deb is free and open source software.
