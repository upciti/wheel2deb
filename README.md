## wheel2deb: python wheel to debian package converter

[![Build Status](https://travis-ci.org/parkoview/wheel2deb.svg?branch=master)](https://travis-ci.org/parkoview/wheel2deb)

**wheel2deb basically takes a list of wheels as input and produces a list of debian CPython packages (those prefixed with python- or python3-).**

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

wheel2deb uses python3-apt to search for debian packages, dpkg-shlibdeps to calculate shared library dependencies and apt-file to search packages providing missing shared library dependencies:
```sh
apt update
apt install python3-apt apt-file dpkg-dev fakeroot
apt-file update
```

If you are converting a pure python wheel, you don't actually need apt-file and dpkg-dev

Check [setup.py](setup.py) for python requirements

## Features

-   guess debian package names from wheel names and search for them in the cache
-   search packages providing shared library dependencies for wheels with native code
-   handle entrypoints and scripts (those will be installed in /usr/bin with a proper shebang)
-   try to locate licence files and to generate a debian/copyright file

## Options

Use `wheel2deb --help` and `wheel2deb build --help` to check all supported options

| Option                    | Description                                                                                         |
| --------------------------| --------------------------------------------------------------------------------------------------- |
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

Copyright Parkoview SA 2019.

Distributed under the terms of the [MIT](https://github.com/parkoview/wheel2deb/blob/master/LICENSE) license, wheel2deb is free and open source software.