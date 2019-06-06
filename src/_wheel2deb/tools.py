from . import logger as logging

logger = logging.getLogger(__name__)


def shell(args, **kwargs):
    """
    Replacement for subprocess.run on platforms without python3.5
    :param args: Command and parameters in a list
    :return: A tuple with (command output, return code)
    """
    import subprocess

    output, returncode = '', 0
    logger.debug('running %s', ' '.join(args))
    try:
        if 'cwd' in kwargs:
            kwargs['cwd'] = str(kwargs['cwd'])
        output = subprocess.check_output(
            args, stderr=subprocess.STDOUT, **kwargs)
    except subprocess.CalledProcessError as e:
        returncode = e.returncode
        output = e.output

    return output.decode('utf-8'), returncode


def install_packages(packages):
    args = 'apt-get -y --no-install-recommends install'.split(' ') + \
           list(packages)
    returncode = shell(args)[1]

    if returncode:
        logger.critical('failed to install dependencies ☹. did you add the '
                        'host architecture with dpkg --add-architecture ?')
    return returncode


def build_package(cwd, arch=None):
    from pathlib import Path
    import re

    # read package arch
    control = (Path(cwd) / 'debian' / 'control').read_text()
    m = re.search(r'Architecture: (\w+)', control)
    if m and not arch:
        arch = m.group(1)

    args = ['dpkg-buildpackage', '-us', '-uc']
    if arch and arch != 'all':
        args += ['--host-arch', arch]

    output, returncode = shell(args, cwd=cwd)
    logger.debug(output)
    if returncode:
        logger.error('failed to build package ☹')

    return returncode


def parse_build_deps(cwd):
    """
    Extract build dependencies from debian/control
    :param cwd: Path to debian source package
    :return: List of build dependencies
    """
    from pathlib import Path
    import re

    control = (Path(cwd) / 'debian' / 'control').read_text()
    for line in control.split('\n'):
        if line.startswith('Build-Depends:'):
            m = re.findall(r'([^=\s,()]+)\s?(?:\([^)]+\))?', line[14:])
            return m

    raise ValueError("could not find Build-Depends in debian/control")


def patch_pathlib():
    def path_read_text(self):
        with self.open('r') as f:
            return f.read()

    from pathlib import Path
    if not hasattr(Path, 'read_text'):
        Path.read_text = path_read_text
