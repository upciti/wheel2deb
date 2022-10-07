import re
from pathlib import Path
from threading import Event, Thread
from time import sleep

from _wheel2deb.logger import logging
from _wheel2deb.utils import shell

logger = logging.getLogger(__name__)


def parse_debian_control(cwd: Path):
    """
    Extract fields from debian/control
    :param cwd: Path to debian source package
    :return: Dict object with fields as keys
    """

    field_re = re.compile(r"^([\w-]+)\s*:\s*(.+)")

    content = (cwd / "debian" / "control").read_text()
    control = {}
    for line in content.split("\n"):
        m = field_re.search(line)
        if m:
            g = m.groups()
            control[g[0]] = g[1]

    for k in ("Build-Depends", "Depends"):
        m = re.findall(r"([^=\s,()]+)\s?(?:\([^)]+\))?", control[k])
        control[k] = m

    return control


def build_package(cwd: Path) -> int:
    """Run dpkg-buildpackage in specified path."""
    args = ["dpkg-buildpackage", "-us", "-uc"]
    arch = parse_debian_control(cwd)["Architecture"]
    if arch != "all":
        args += ["--host-arch", arch]

    stdout, returncode = shell(args, cwd=cwd)
    logger.debug(stdout)
    if returncode:
        logger.error(f'failed to build package in "{cwd}" ☹')

    return returncode


def build_packages(paths, threads: int = 4) -> None:
    """
    Run several instances of dpkg-buildpackage in parallel.
    :param paths: List of paths where dpkg-buildpackage will be called
    :param threads: Number of threads to run in parallel
    """

    paths = paths.copy()
    workers = []
    for i in range(threads):
        event = Event()
        event.set()
        workers.append(dict(done=event, path=None))

    def build(done, path):
        logger.info(f"building {path}")
        build_package(path)
        done.set()

    while False in [w["done"].is_set() for w in workers] or paths:
        for w in workers:
            if w["done"].is_set() and paths:
                w["done"].clear()
                w["path"] = paths.pop()
                Thread(target=build, kwargs=w).start()
        sleep(1)
