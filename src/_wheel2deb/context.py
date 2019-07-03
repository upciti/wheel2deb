import attr
import platform

from .pyvers import Version


@attr.s
class Context:
    maintainer_name = attr.ib(default='wheel2deb')
    maintainer_email = attr.ib(default='wheel2deb@parkoview.com')
    distribution = attr.ib(default='unstable')
    python_version = attr.ib(
        converter=lambda x: Version.from_str(x) if isinstance(x, str) else x,
        default=platform.python_version())
    ignore_entry_points = attr.ib(default=False)
    ignore_upstream_versions = attr.ib(default=False)
    ignore_requirements = attr.ib(factory=list)
    map = attr.ib(factory=dict)
    depends = attr.ib(factory=list)
    provides = attr.ib(factory=list)
    revision = attr.ib(default='1')
    epoch = attr.ib(default=0, converter=int)
    version_template = attr.ib(
        default='{epoch}:{upstream_version}-{revision}~w2d{w2d_version[0]}')


@attr.s
class Settings:
    root_ctx = attr.ib(type=Context)
    config = attr.ib(type=dict)

    def update(self, changes):
        args = changes.copy()
        for k, v in changes.items():
            if not v or not hasattr(self.root_ctx, k):
                args.pop(k)
        self.root_ctx = attr.evolve(self.root_ctx, **args)

    def get_ctx(self, key=None):
        changes = {}

        if key is None:
            return self.root_ctx

        for k in self.config.keys():
            if key.startswith(k):
                changes = self.config[k]
        return attr.evolve(self.root_ctx, **changes)


def load(file):
    root_ctx = Context()
    config = {}
    try:
        with open(file, 'r') as f:
            import yaml
            config = yaml.safe_load(f)
            if 'all' in config:
                root_ctx = attr.evolve(root_ctx, **config['all'])
    except FileNotFoundError:
        pass
    return Settings(root_ctx, config)
