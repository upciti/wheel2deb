import attr
import platform
import re

from .pyvers import Version


@attr.s
class Context:
    maintainer_name = attr.ib(default="wheel2deb")
    maintainer_email = attr.ib(default="wheel2deb@upciti.com")
    distribution = attr.ib(default="unstable")
    python_version = attr.ib(
        converter=lambda x: Version.from_str(x) if isinstance(x, str) else x,
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


def load(file=None):
    with open(file, "r") as f:
        import yaml

        config = yaml.safe_load(f)
    return Settings(config)
