import os.path
import attr
import re
import glob
from tempfile import mkdtemp
from functools import lru_cache
from pathlib import Path
from packaging import specifiers, version
from packaging.requirements import Requirement
from wheel.wheelfile import WheelFile
from pkginfo import Distribution

from .logger import logging
from .pyvers import VersionRange, Version

logger = logging.getLogger(__name__)

WHEEL_NAME_RE = re.compile(
    r"^(?P<name>.+)-(?P<version>.+)-(?P<python_tag>[pcij].+)"
    r"-(?P<abi_tag>.+)-(?P<platform_tag>.+).whl$"
)


@attr.s(frozen=True)
class Record:
    """
    Entries of *.dist-info/RECORD organized in categories
    """

    LICENSE_RE = re.compile(r"license", re.IGNORECASE)
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
                logger.debug("found license: %s", file)
                record.licenses.append(file)
                continue

            if ".data/scripts/" in file:
                logger.debug("found script: %s", file)
                record.scripts.append(file)
                continue

            if re.findall(cls.SHLIBS_RE, os.path.basename(file)):
                logger.debug("found shared lib: %s", file)
                record.libs.append(file)

            if file:
                # everything else
                record.files.append(file)

        record.lib_dirs.extend(list(set(os.path.dirname(x) for x in record.libs)))

        return record


class Metadata(Distribution):
    def __init__(self, content):
        self.parse(content)

    def read(self):
        pass


class Wheel:
    def __init__(self, filepath, extract_path=None):

        # relative path to wheel file
        self.filepath = Path(filepath)
        self.filename = self.filepath.name
        self.extract_path = (
            Path(extract_path) if extract_path else Path(mkdtemp()) / self.filename[:-4]
        )

        if not filepath.exists():
            raise ValueError("No such file: %s" % filepath)

        if not self.filename.endswith(".whl"):
            raise ValueError("Not a known wheel archive format: %s" % filepath)

        # parse wheel name
        # https://www.python.org/dev/peps/pep-0425
        g = re.match(WHEEL_NAME_RE, self.filename).groupdict()
        self.name = normalize_name(g["name"])
        self.version = g["version"]
        self.python_tag = g["python_tag"]
        self.abi_tag = g["abi_tag"]
        self.platform_tag = g["platform_tag"]

        self._unpack()
        self._parse()

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

    @lru_cache(maxsize=None)
    def version_range(self, pyvers):
        m = re.search(r"(\d)(\d)", self.python_tag)
        if m:
            v = Version(*m.groups())
            if pyvers.major != v.major:
                return None
            else:
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

    @lru_cache(maxsize=None)
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

    @property
    @lru_cache(maxsize=None)
    def cpython_supported(self):
        if re.search(r"(?:py|cp)", self.python_tag):
            return True
        return False

    def _unpack(self):
        """
        Unpack wheel archive
        """
        if self.extract_path.exists():
            return

        with WheelFile(str(self.filepath)) as wf:
            logger.debug("unpacking wheel to: %s..." % self.extract_path)
            wf.extractall(str(self.extract_path))

    def __repr__(self):
        return self.filename

    def _parse(self):
        info_dir = Path(glob.glob(str(self.extract_path / "*.dist-info"))[0])

        # parse .dist-info/METADATA
        self.metadata = Metadata((info_dir / "METADATA").read_text())

        # parse .dist-info/RECORD
        self.record = Record.from_str((info_dir / "RECORD").read_text())

        try:
            # parse .dist-info/entry_points.txt
            self.entrypoints = (info_dir / "entry_points.txt").read_text()
        except FileNotFoundError:
            self.entrypoints = None


def normalize_name(name):
    """
    All comparisons of distribution names MUST be case insensitive,
    and MUST consider hyphens and underscores to be equivalent.
    https://www.python.org/dev/peps/pep-0426/#name
    """
    return name.replace("-", "_").lower()
