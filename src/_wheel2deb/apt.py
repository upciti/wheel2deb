import attr
import apt
import re
from .logger import logging

# https://www.debian.org/doc/debian-policy/ch-controlfields.html#version
PACKAGE_VER_RE = re0 = re.compile(
    r"^(?:(?P<epoch>\d+):)?"
    r"(?P<version>(?:[\w\.~\-]+(?=-(?P<revision>[^-]+$)))|[\w\.~\-]+)"
)

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


def search_packages(names, arch):
    if not names:
        return

    global _cache
    if not _cache:
        _cache = apt.Cache()
        _cache.open()

    logger.debug("searching %s in apt cache...", " ".join(names))

    for name in names:
        if name in _cache:
            yield Package.factory(name, _cache[name].versions[0].version)
        elif arch and name + ":" + arch in _cache:
            yield Package.factory(name, _cache[name + ":" + arch].versions[0].version)
        else:
            yield None
