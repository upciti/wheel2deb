import platform
import re
import sys
from pathlib import Path

import attr
import yaml

from wheel2deb import logger as logging
from wheel2deb.pyvers import Version
from wheel2deb.version import __version__

logger = logging.getLogger(__name__)


@attr.s
class Context:
    maintainer_name = attr.ib(default="wheel2deb")
    maintainer_email = attr.ib(default="wheel2deb@upciti.com")
    distribution = attr.ib(default="unstable")
    python_version = attr.ib(
        converter=lambda x: Version.from_str(x) if isinstance(x, str) else x,
        on_setattr=attr.setters.convert,
        default=platform.python_version(),
    )
    platform_machine = attr.ib(default=platform.machine())
    arch = attr.ib(default="")
    ignore_entry_points = attr.ib(default=False)
    ignore_upstream_versions = attr.ib(default=False)
    ignore_requirements = attr.ib(factory=list)
    ignore_specifiers = attr.ib(factory=list)
    extra = attr.ib(default="")
    map = attr.ib(factory=dict)
    depends = attr.ib(factory=list)
    conflicts = attr.ib(factory=list)
    provides = attr.ib(factory=list)
    revision = attr.ib(default="1")
    epoch = attr.ib(default=0, converter=int)
    version_template = attr.ib(
        default="{epoch}:{upstream_version}-{revision}~w2d{w2d_version[0]}"
    )
    extended_desc = attr.ib(
        default="This package was generated by wheel2deb v" + str(__version__)
    )

    def update(self, changes):
        for k, v in changes.items():
            if v and hasattr(self, k):
                setattr(self, k, changes[k])


@attr.s
class Settings:
    config = attr.ib(factory=dict)
    default_ctx = attr.ib(factory=Context)

    def get_ctx(self, key):
        ctx = self.default_ctx
        for k in self.config.keys():
            if re.match(k, key):
                ctx = attr.evolve(ctx, **self.config[k])
        return ctx


def load_configuration(configuration_path: Path | None) -> Settings:
    default_configuration_path = Path("wheel2deb.yml")

    if configuration_path is None and default_configuration_path.is_file():
        configuration_path = default_configuration_path

    if configuration_path is None:
        return Settings()

    if configuration_path.exists() is False:
        logger.error(f"Configuration {configuration_path} does not exist")
        sys.exit(1)

    if configuration_path.is_file() is False:
        logger.error(f"{configuration_path} is not a file")
        sys.exit(1)

    try:
        configuration = yaml.safe_load(configuration_path.read_text())
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in configuration file: {e}")
        sys.exit(1)

    return Settings(configuration)
