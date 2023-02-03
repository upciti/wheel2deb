import re
from functools import lru_cache
from typing import Optional

import attr

from wheel2deb import logger as logging
from wheel2deb.utils import shell

# https://www.debian.org/doc/debian-policy/ch-controlfields.html#version
PACKAGE_VER_RE = re.compile(
    r"^(?:(?P<epoch>\d+):)?"
    r"(?P<version>(?:[\w\.~\-]+(?=-(?P<revision>[^-]+$)))|[\w\.~\-]+)"
)

APT_CACHE_MADISON_RE = re.compile(r"[^|]+\|([^|]+)\|[^|]+")

logger = logging.getLogger(__name__)

_cache = None


@attr.s(frozen=True)
class Package:
    # package name
    name = attr.ib(type=str)
    # upstream version
    version = attr.ib(type=str)
    # debian revision
    revision = attr.ib(type=str)
    epoch = attr.ib(type=str)

    @classmethod
    def factory(cls, name, pkg_version):
        g = PACKAGE_VER_RE.match(pkg_version).groupdict()
        return cls(name, **g)

    def __str__(self):
        # show only package name and upstream version
        return "{}=={}".format(self.name, self.version)


@lru_cache
def search_package(name, arch) -> Optional[Package]:
    name = name + ":" + arch if arch else name
    output, _ = shell(["apt-cache", "madison", name])
    match = APT_CACHE_MADISON_RE.match(output)
    return Package.factory(name, match.group(1).strip()) if match is not None else None


def search_packages(names, arch):
    if not names:
        return

    logger.debug(f"searching {' '.join(names)} in apt cache...")

    for name in names:
        yield search_package(name, arch)
