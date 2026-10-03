## wheel2deb

![cicd](https://github.com/upciti/wheel2deb/actions/workflows/cicd.yml/badge.svg)
[![codecov](https://codecov.io/gh/upciti/wheel2deb/branch/main/graph/badge.svg)](https://codecov.io/gh/upciti/wheel2deb)
[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![PyPI version shields.io](https://img.shields.io/pypi/v/wheel2deb.svg)](https://pypi.python.org/pypi/wheel2deb/)
[![Downloads](https://static.pepy.tech/personalized-badge/wheel2deb?period=total&units=international_system&left_color=blue&right_color=green&left_text=Downloads)](https://pepy.tech/project/wheel2deb)
[![WakeMeOps](https://docs.wakemeops.com/badges/wheel2deb.svg)](https://docs.wakemeops.com/packages/wheel2deb)

`wheel2deb` is a python wheel to debian package converter. It takes a list of wheels as input and produces a list of debian binary CPython packages (those prefixed with python- or python3-).

[![asciicast](https://asciinema.org/a/249779.svg)](https://asciinema.org/a/249779)

## Quick Example

The following shows how to convert numpy and pytest, along with their dependencies into a list of debian packages:

```sh
# Download (and build if needed) pytest, numpy and their requirements
pip3 wheel pytest numpy
# Convert all wheels to debian source packages, build them with dpkg-buildpackage
wheel2deb
ls -l output/*.deb
# Install generated packages
dpkg -i output/*.deb
# Run pytest on numpy
python3 -c "import numpy; numpy.test()"
```

## Project scope

- Python 2.7 and 3
- CPython only for now
- support for non pure python wheels
- support debian architectures all, armhf, amd64, i686
- tested on jessie, stretch, buster so far, ubuntu should also work

## Requirements

`wheel2deb` uses `apt-cache` to search for debian packages, `dpkg-shlibdeps` to calculate shared library dependencies and `apt-file` to search packages providing shared library dependencies. `wheel2deb build` requires the usual tools to build a debian package:

```sh
apt update
apt install apt-file dpkg-dev fakeroot build-essential devscripts debhelper
apt-file update
```

If you want to cross build packages for ARM, you will also need to install `binutils-arm-linux-gnueabihf`.

Converting pure python wheels, don't actually requires apt-file and dpkg-dev.

Keep in mind that you should only convert wheels that have been built for your distribution and architecture. wheel2deb will not warn you about ABI compatibility issues.

## Installation

### From the release page

`wheel2deb` is packaged as a single binary application that you can download from the release page. Using those releases will spare you the hassle of building Python 3.11 on old Debian based distributions.

### With [wakemeops](https://docs.wakemeops.com)

```shell
sudo apt-get install wheel2deb
```

### With docker

Pre-built images are published to **GitHub Container Registry**:

```shell
docker pull ghcr.io/upciti/wheel2deb:latest
docker run --rm ghcr.io/upciti/wheel2deb --help
```

Or build from source using the multi-stage Dockerfile:

```shell
docker build -t wheel2deb .
docker run --rm wheel2deb --help
```

To build a specific version (CI), pass the VERSION build arg:

```shell
docker build --build-arg VERSION=1.2.3 -t wheel2deb .
docker run --rm wheel2deb version
# Output: 1.2.3
```

**Example: convert requests wheel to .deb**

```shell
# 1. Download wheel
pip wheel requests -w wheels/ --no-deps

# 2. Prepare output dir (UID 1000 = container user)
sudo mkdir -p output && sudo chown -R 1000:1000 output/

# 3. Convert wheel to deb
docker run --rm \
  -v "$PWD/wheels:/wheels" \
  -v "$PWD/output:/home/user/output" \
  ghcr.io/upciti/wheel2deb:latest \
  --search-path /wheels

# 4. Install
sudo dpkg -i output/python3-requests_*.deb
```

### With [pipx](https://github.com/pipxproject/pipx)

`wheel2deb` is available from [pypi](https://pypi.org/project/wheel2deb/):

```shell
pipx install wheel2deb
```

## Features

- guess debian package names from wheel names and search for them in the cache
- search packages providing shared library dependencies for wheels with native code
- handle entrypoints and scripts (those will be installed in /usr/bin with a proper shebang)
- try to locate licence files and to generate a debian/copyright file

## Usage

Use `wheel2deb convert --help` and `wheel2deb build --help` to check all supported options.

## Development

You will need [poetry](https://python-poetry.org/), and probably [pyenv](https://github.com/pyenv/pyenv) if you don't have python 3.11 on your host.

```shell
poetry install
```

To run wheel2deb test suite run:

```shell
poetry run task check
```

To build a python wheel:

```shell
poetry run poetry build
```

## Bugs/Requests

Please use the [GitHub issue tracker](https://github.com/upciti/wheel2deb/issues) to submit bugs or request features.

## License

Copyright Parkoview SA 2019-2023.

Distributed under the terms of the [MIT](https://github.com/upciti/wheel2deb/blob/master/LICENSE) license, wheel2deb is free and open source software.
