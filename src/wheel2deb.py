import argparse
import os
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
                   help='Output directory (defaults to ./output)')
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
        split = partial(str.split, sep='=', maxsplit=2)
        args.map = {x: y for x, y in list(map(split, args.map))}

    args.output = Path(args.output)

    return args


def debianize(args):
    """
    Convert wheels found in args.search_paths in debian source packages
    """

    # load config file (may contain a root context, and/or per wheel contexts)
    settings = load('wheel2deb.yml')
    # command line arguments take precedence over config file
    settings.update(vars(args))

    if not args.output.exists():
        args.output.mkdir()

    # list all python wheels in search paths
    files = []
    for path in [Path(path) for path in args.search_paths]:
        files.extend(path.glob('*.whl'))
    files = sorted(files, key=lambda x: x.name)

    filenames = list(map(lambda x: x.name, files))
    if not args.include:
        args.include = filenames

    # remove excluded wheels
    if args.exclude:
        args.include = \
            list(filter(lambda x: x not in args.exclude, args.include))

    # fail if some input wheel was not found in search paths
    missing = list(filter(lambda x: x not in filenames, args.include))
    if missing:
        logger.critical('File(s) not found: %s', ', '.join(missing))
        exit(1)

    logger.task('Unpacking %s wheels', len(files))

    wheels = []
    for file in files:
        path = args.output / file.name[:-4] / 'src'
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
    p.add_argument('-f', '--force', action='store_true',
                   help='Build source package even if .deb already exists')
    p.add_argument('-j', '--threads', default=4, type=int,
                   help='Worker threads count')

    args = p.parse_args(argv)

    packages = list(Path(args.path).glob('*.deb'))

    # list source packages in user supplied path
    src_packages = []
    for d in os.listdir(str(args.path)):
        path = Path(args.path) / d
        if path.is_dir() and (path / 'debian/control').is_file():
            src_packages.append(path)

    build_deps = set()
    for path in src_packages.copy():
        control = tools.parse_debian_control(path)
        if not args.force and True in [p.name.startswith(
                control['Package'] + '_') for p in packages]:
            # source package already built, skipping build
            src_packages.remove(path)
        else:
            # never built, add build deps to list
            build_deps.update(control['Build-Depends'])

    logger.task('Installing %s build dependencies...', len(build_deps))
    if build_deps and src_packages:
        tools.install_packages(build_deps)

    logger.task('Building %s source packages...', len(src_packages))
    tools.build_packages(src_packages, args.threads)


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

    # the return code is the number of errors
    exit(logging.get_error_counter())


if __name__ == '__main__':
    main()
