import glob
import argparse
import os
import sys
import time
from pathlib import Path
from logging import INFO, DEBUG
from functools import partial
from _wheel2deb import tools
from _wheel2deb import logger as logging
from _wheel2deb.context import load
from _wheel2deb.pydist import Wheel
from _wheel2deb.debian import SourcePackage

logger = logging.getLogger(__name__)

tools.patch_pathlib()


def parse_args(argv):
    p = argparse.ArgumentParser(
        description='Python Wheel to Debian package converter')

    p.add_argument('-v', '--verbose', action='store_true',
                   help='Enable debug logs')
    p.add_argument('-i', '--include', nargs='+',
                   help='List of wheel names to convert')
    p.add_argument('-e', '--exclude', nargs='+',
                   help='List of wheel names not to convert')
    p.add_argument('-o', '--output', default='output',
                   help='Output directory (defaults to current directory)')
    p.add_argument('--python-version',
                   help='cpython version on the target debian distribution '
                        '(defaults to the platform version)')
    p.add_argument('-x', '--search-paths', default='.', nargs='+',
                   help='')
    p.add_argument('--map', nargs='+',
                   help='')
    p.add_argument('--depends', nargs='+',
                   help='')
    p.add_argument('--epoch',
                   help='Debian package epoch (defaults to 0)')
    p.add_argument('--revision',
                   help='Debian package revision (defaults to 1)')
    p.add_argument('--ignore-entry-points', action='store_true',
                   help='Don\'t include entry points in debian package')
    p.add_argument('--ignore-upstream-version', action='store_true',
                   help='Ignore version specifiers from wheel requirements')

    args = p.parse_args(argv)

    if args.map:
        split_part = partial(str.split, sep='=', maxsplit=2)
        args.map = {x: y for x, y in [split_part(x) for x in args.map]}

    args.output = Path(args.output)

    return args


def debianize(args):
    """
    Convert wheels found in args.search_paths in debian source packages
    """

    # load config file (may contain a root context, and/or per wheel contexts)
    settings = load('whee2deb.yml')
    # command line arguments take precedence over config file
    settings.update(vars(args))

    if not args.output.exists():
        args.output.mkdir()

    # list all python wheels in search paths
    files = []
    for path in args.search_paths:
        files.extend(glob.glob(os.path.join(path, '*.whl')))
    files = sorted(files, key=lambda x: os.path.basename(x))

    filenames = [os.path.basename(x) for x in files]
    if not args.include:
        args.include = filenames

    # remove excluded wheels
    if args.exclude:
        args.include = [x for x in args.include if x not in args.exclude]
    # fail if some input wheel was not found in search paths
    missing = [x for x in args.include if x not in filenames]
    if missing:
        logger.critical('File(s) not found: %s', ', '.join(missing))
        exit(1)

    logger.task('Unpacking %s wheels', len(files))

    wheels = []
    for file in files:
        path = args.output / file[:-4] / 'src'
        wheel = Wheel(file, path)
        ctx = settings.get_ctx(wheel.filename)

        if not wheel.cpython_supported:
            # ignore wheels that are not cpython compatible
            logger.warning('%s does not support cpython', wheel.filename)
            continue

        if not wheel.version_supported(ctx.python_version):
            # ignore wheels that are not compatible specified python version
            logger.warning('%s does not support python %s',
                           wheel.filename, ctx.python_version)
            continue

        logger.info('%s', wheel.filename)
        wheels.append(wheel)

    packages = []
    for wheel in wheels:
        if wheel.filename in args.include:
            logger.task('Debianizing wheel %s', wheel)
            ctx = settings.get_ctx(wheel.filename)
            package = SourcePackage(ctx, wheel, extras=wheels)
            package.create()
            packages.append(package)


def build(argv):
    """
    Install build dependencies and build all debian source packages
    """

    p = argparse.ArgumentParser(
        description='Build debian source packages')

    p.add_argument('-v', '--verbose', action='store_true',
                   help='Enable debug logs')
    p.add_argument('-p', '--path', default='output',
                   help='Path to search for source packages '
                        '(defaults to "./output")')

    args = p.parse_args(argv)

    src_packages = []
    for d in os.listdir(str(args.path)):
        path = Path(args.path) / d
        if path.is_dir() and (path / 'debian/control').is_file():
            src_packages.append(path)

    build_deps = set()
    for path in src_packages:
        build_deps.update(tools.parse_build_deps(path))
    if build_deps:
        logger.task('Installing %s build dependencies...', len(build_deps))
        tools.install_packages(build_deps)

    for path in src_packages:
        logger.task('Building debian source package in %s', path)
        tools.build_package(path)


def main():
    start_time = time.time()

    p = argparse.ArgumentParser(add_help=False)
    p.add_argument('-v', '--verbose', action='store_true')

    args, argv = p.parse_known_args()

    if args.verbose:
        logging.getLogger().setLevel(DEBUG)
    else:
        logging.getLogger().setLevel(INFO)

    if argv and argv[0] == 'build':
        build(argv[1:])
    else:
        args = parse_args(argv)
        debianize(args)

    logger.summary('\nWarnings: %s. Errors: %s. Elapsed: %ss.',
                   logging.get_warning_counter(), logging.get_error_counter(),
                   round(time.time()-start_time, 3))

    if logging.get_error_counter():
        exit(1)


if __name__ == '__main__':
    main()
