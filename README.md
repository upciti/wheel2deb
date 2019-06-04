[![asciicast](https://asciinema.org/a/249779.svg)](https://asciinema.org/a/249779)

## Quick Example

```
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

## Features

- TODO

## Bugs/Requests

Please use the [GitHub issue tracker](<https://github.com/parkoview/wheel2deb/issues>) to submit bugs or request features.

## License

Copyright Parkoview SA 2019.

Distributed under the terms of the [MIT](https://github.com/parkoview/wheel2deb/blob/master/LICENSE) license, pytest is free and open source software.

