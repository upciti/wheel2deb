import configparser
import os.path
import re
from dataclasses import dataclass
from functools import cached_property, lru_cache
from pathlib import Path
from typing import List

import attr
from packaging import specifiers, version
from packaging.requirements import Requirement
from pkginfo import Distribution
from wheel.wheelfile import WheelFile

from wheel2deb import logger as logging
from wheel2deb.pyvers import Version, VersionRange

logger = logging.getLogger(__name__)

EXTRACT_PATH = Path("/tmp/wheel2deb")

WHEEL_NAME_RE = re.compile(
    r"^(?P<name>.+)-(?P<version>.+)-(?P<python_tag>[pcij].+)"
    r"-(?P<abi_tag>.+)-(?P<platform_tag>.+).whl$"
)


def normalize_name(name):
    """
    All comparisons of distribution names MUST be case insensitive,
    and MUST consider hyphens and underscores to be equivalent.
    https://www.python.org/dev/peps/pep-0426/#name
    """
    return name.replace("-", "_").lower()


@dataclass
class Entrypoint:
    name: str
    module: str
    function: str


@attr.s(frozen=True)
class Record:
    """
    Entries of *.dist-info/RECORD organized in categories
    """

    LICENSE_RE = re.compile(r"(^|[^\w])license(\..*)?$", re.IGNORECASE)
    SHLIBS_RE = re.compile(r"\.so[.\d]*")

    libs = attr.ib(factory=list)
    lib_dirs = attr.ib(factory=list)
    licenses = attr.ib(factory=list)
    scripts = attr.ib(factory=list)
    files = attr.ib(factory=list)

    @classmethod
    def from_str(cls, content):
        files = [line.rstrip().split(",")[0] for line in content.split("\n")]
        record = Record()
        for file in files:
            if re.search(cls.LICENSE_RE, file):
                logger.debug(f"found license: {file}")
                record.licenses.append(file)
                continue

            if ".data/scripts/" in file:
                logger.debug(f"found script: {file}")
                record.scripts.append(file)
                continue

            if re.findall(cls.SHLIBS_RE, os.path.basename(file)):
                logger.debug(f"found shared lib: {file}")
                record.libs.append(file)

            if file:
                # everything else
                record.files.append(file)

        record.lib_dirs.extend(list({os.path.dirname(x) for x in record.libs}))

        return record


class Metadata(Distribution):
    def __init__(self, content):
        self.parse(content)

    def read(self):
        pass


class Wheel:
    def __init__(self, wheel_name: str, extract_path: Path) -> None:
        self.wheel_name = wheel_name
        self.extract_path = extract_path
        self.info_dir = next(iter(self.extract_path.glob("*.dist-info")))

        # parse wheel name, see https://www.python.org/dev/peps/pep-0425
        g = re.match(WHEEL_NAME_RE, self.wheel_name).groupdict()
        self.name = normalize_name(g["name"])
        self.version = g["version"]
        self.python_tag = g["python_tag"]
        self.abi_tag = g["abi_tag"]
        self.platform_tag = g["platform_tag"]

    @cached_property
    def metadata(self) -> Metadata:
        return Metadata((self.info_dir / "METADATA").read_text())

    @cached_property
    def record(self) -> Record:
        return Record.from_str((self.info_dir / "RECORD").read_text())

    @cached_property
    def entrypoints(self) -> List[Entrypoint]:
        entrypoints = []
        try:
            config = configparser.ConfigParser()
            config.read_string((self.info_dir / "entry_points.txt").read_text())
            if "console_scripts" in config.sections():
                name, path = config.items("console_scripts")[0]
                entrypoints.append(Entrypoint(name, *(path.split(":"))))
        except FileNotFoundError:
            pass
        return entrypoints

    def requires(self, env=None):
        if not env:
            env = {"extra": ""}
        elif env and "extra" not in env:
            env["extra"] = ""
        reqs = [Requirement(req) for req in self.metadata.requires_dist]
        reqs = filter(lambda r: not r.marker or r.marker.evaluate(env), reqs)
        reqs = list(reqs)
        for req in reqs:
            req.name = normalize_name(req.name)
        return reqs

    @lru_cache
    def version_range(self, pyvers):
        m = re.search(r"(\d)(\d+)", self.python_tag)

        if m:
            v = Version(*m.groups())
            if pyvers.major != v.major:
                return None
            else:
                if self.abi_tag == "abi3":
                    return VersionRange(v, None)
                return VersionRange(v, v.inc())

        # TODO: use requires_python ?
        versions = []
        for classifier in self.metadata.classifiers:
            m = re.match(r"Programming Language :: Python :: ([\d.]+)", classifier)
            if m:
                version = Version.from_str(m.group(1))
                if version.major == pyvers.major and version.minor != 0:
                    versions.append(version)
        sorted(versions)

        if versions:
            # assume versions[0] and up supported
            return VersionRange(versions[0], None)

        # unable to compute python version range
        # supported by that wheel
        return None

    @lru_cache
    def version_supported(self, pyvers):
        m = re.search(r"(?:py|cp)%s" % pyvers.major, self.python_tag)
        if not m:
            return False

        requires_python = self.metadata.requires_python
        if self.metadata.requires_python is None:
            # The package provides no information
            return True

        requires_python_specifier = specifiers.SpecifierSet(requires_python)
        python_version = version.parse(str(pyvers))
        return python_version in requires_python_specifier

    @cached_property
    def cpython_supported(self):
        if re.search(r"(?:py|cp)", self.python_tag):
            return True
        return False

    def __repr__(self):
        return self.wheel_name


def parse_wheel(wheel_path: Path, base_extract_path: Path = EXTRACT_PATH) -> Wheel:
    extract_path = base_extract_path / wheel_path.name[:-4]
    if extract_path.exists() is False:
        with WheelFile(str(wheel_path)) as wf:
            logger.debug(f"unpacking wheel to: {extract_path}...")
            wf.extractall(str(extract_path))
    return Wheel(wheel_path.name, extract_path)
