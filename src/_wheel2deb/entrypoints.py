import os
import configparser
from setuptools.command.install_scripts import install_scripts
from setuptools.dist import Distribution


def parse_entry_points(content):
    config = configparser.ConfigParser()
    config.read_string(content)

    entry_points = {}
    for section in config:
        x = list(map(lambda k: '%s=%s' % k, config.items(section)))
        if x:
            entry_points[section] = x

    return entry_points


def run_install_scripts(wheel, pyvers, cwd):
    settings = dict(
        name=wheel.name,
        entry_points=wheel.entrypoints,
        version=wheel.version,
    )
    dist = Distribution(settings)
    dist.script_name = 'setup.py'
    cmd = install_scripts(dist)
    cmd.install_dir = os.path.abspath(os.path.join(str(cwd), 'entrypoints'))
    bs = cmd.get_finalized_command('build_scripts')
    bs.executable = '/usr/bin/python'+str(pyvers.major)
    cmd.ensure_finalized()
    # cmd.run() creates some files that we don't want in python cwd
    oldcwd = os.getcwd()
    os.chdir('/tmp')
    try:
        cmd.run()
    finally:
        os.chdir(oldcwd)
