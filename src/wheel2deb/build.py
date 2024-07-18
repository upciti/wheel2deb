import re
from pathlib import Path
from threading import Event, Thread
from time import sleep
from typing import List

from wheel2deb import logger as logging
from wheel2deb.utils import shell

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


def build_packages(paths: List[Path], threads: int, force_build: bool) -> None:
    """
    Run several instances of dpkg-buildpackage in parallel.
    :param paths: List of paths where dpkg-buildpackage will be called
    :param threads: Number of threads to run in parallel
    """

    paths = [p for p in paths if not Path(str(p) + ".deb").is_file() or force_build]
    logger.task(f"Building {len(paths)} source packages...")

    workers = []
    for i in range(threads):
        event = Event()
        event.set()
        workers.append({"done": event, "path": None})

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


def build_all_packages(output_directory: Path, workers: int, force_build: bool) -> None:
    """
    Build debian source packages in parallel.
    :param output_directory: path where to search for source packages
    :param workers: Number of threads to run in parallel
    :param force_build: Build packages even if .deb already exists
    """

    if output_directory.exists() is False:
        logger.error(f"Directory {output_directory} does not exist")
        return

    if output_directory.is_dir() is False:
        logger.error(f"{output_directory} is not a directory")
        return

    paths = []
    for output_directory in output_directory.iterdir():
        if output_directory.is_dir() and (output_directory / "debian/control").is_file():
            paths.append(output_directory)

    build_packages(paths, workers, force_build)
