import re
from pathlib import Path
from typing import List

from dirsync import sync

from wheel2deb import logger as logging
from wheel2deb.context import Settings
from wheel2deb.depends import normalize_package_version, search_python_deps, suggest_name
from wheel2deb.pydist import Wheel, parse_wheel
from wheel2deb.templates import environment
from wheel2deb.utils import shell
from wheel2deb.version import __version__

logger = logging.getLogger(__name__)
dirsync_logger = logging.getLogger("dirsync")
dirsync_logger.setLevel(logging.ERROR)


COPYRIGHT_RE = re.compile(
    r"(?:copyrights?|\s*©|\s*\(c\))[\s:|,]*" r"((?=.*[a-z])\d{2,4}(?:(?!all\srights).)+)",
    re.IGNORECASE,
)

DPKG_SHLIBS_RE = re.compile(r"find library (.+\.so[.\d]*) needed")

APT_FILE_RE = re.compile(r"(.*lib.+):\s(?:/usr/lib/|/lib/)")


def platform_to_arch(platform_tag):
    translation_table = {
        "x86_64": "amd64",
        "i686": "i686",
        "armv7l": "armhf",
        "armv6l": "armhf",
        "aarch64": "arm64",
        "any": "all",
    }
    for k, v in translation_table.items():
        if k in platform_tag:
            return v
    return None


class SourcePackage:
    """
    Create a debian source package that can be built
    with dpkg-buildpackage from a python wheel
    """

    def __init__(self, ctx, wheel: Wheel, output, extras=None):
        self.wheel = wheel
        self.ctx = ctx
        self.pyvers = ctx.python_version

        # debian package name
        self.name = suggest_name(ctx, wheel.name)

        # debian package version
        self.version = ctx.version_template.format(
            epoch=ctx.epoch,
            upstream_version=normalize_package_version(self.wheel.version),
            revision=ctx.revision,
            w2d_version=__version__,
        )

        # debian package homepage
        self.homepage = wheel.metadata.home_page
        # debian package description
        self.description = wheel.metadata.summary
        # debian package extended description
        self.extended_desc = ctx.extended_desc
        # upstream license
        self.license = wheel.metadata.license or "custom"

        # debian package architecture
        arch = platform_to_arch(wheel.platform_tag)
        self.arch = arch or "all"
        if not arch:
            logger.error("unknown platform tag, assuming arch=all")

        version_without_epoch = self.version.split(":")[-1]
        # debian package full filename
        self.filename = f"{self.name}_{version_without_epoch}_{self.arch}.deb"

        # root directory of the debian source package
        self.root = Path(output) / self.filename[:-4]
        # contains the files extracted from the wheel
        self.src = Path("src")
        # debian directory path
        # holds the package config files
        self.debian = self.root / "debian"

        # sync src directory with files from the wheel
        sync(
            str(wheel.extract_path),
            str(self.root / self.src),
            "sync",
            create=True,
            logger=dirsync_logger,
        )

        self.interpreter = "python" if self.pyvers.major == 2 else "python3"

        # compute package run dependencies
        self.depends = [f"{self.interpreter}:any"]
        if vrange := wheel.version_range(self.pyvers):
            if vrange.max:
                self.depends.append(f"{self.interpreter} (<< {vrange.max})")
            if vrange.min:
                self.depends.append(f"{self.interpreter} (>= {vrange.min}~)")

        deps, missing = search_python_deps(ctx, wheel, extras)
        self.depends.extend(deps)
        self.depends.extend(ctx.depends)

        # write unsatisfied requirements in missing.txt
        (self.root / "missing.txt").write_text("\n".join(missing) + "\n")

    def install_console_scripts(self) -> None:
        output_path = self.root / "entrypoints"
        output_path.mkdir(exist_ok=True)
        for entrypoint in self.wheel.entrypoints:
            template = environment.get_template("entrypoint")
            script_path = str(output_path / entrypoint.name)
            template.stream(pyvers=self.pyvers, entrypoint=entrypoint).dump(script_path)

    def install(self):
        """Generate debian/install"""

        install = set()

        # wheel modules install path
        if self.pyvers.major == 2:
            destination_path = "/usr/lib/python2.7/dist-packages/"
        else:
            destination_path = "/usr/lib/python3/dist-packages/"

        for absolute_source_path in (self.root / self.src).iterdir():
            source_path = absolute_source_path.relative_to(self.root)
            if not source_path.name.endswith(".data"):
                install.add(f"{source_path} {destination_path}")
            else:
                if (absolute_source_path / "purelib").exists():
                    install.add(f"{source_path / 'purelib/*'} {destination_path}")

        if self.wheel.entrypoints and not self.ctx.ignore_entry_points:
            self.install_console_scripts()
            install.add("entrypoints/* /usr/bin/")

        for script in self.wheel.record.scripts:
            install.add(f"{self.src / script} /usr/bin")

        (self.debian / "install").write_text("\n".join(install))

    def rules(self):
        """Generate debian/rules"""

        self.dump_template(
            "rules",
            shlibdeps_params="".join(
                [" -l" + str(self.src / x) for x in self.wheel.record.lib_dirs]
            ),
        )

    def copyright(self):
        """
        Generate debian/copyright
        https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
        """
        licenses = self.wheel.record.licenses
        license_file = None
        license_content = ""
        copyrights = set()

        if not licenses:
            logger.warning("no license found !")
            return

        # gather copyrights from all licenses
        for lic in licenses:
            content = (self.wheel.extract_path / lic).read_text()
            copyrights.update(set(re.findall(COPYRIGHT_RE, content)))

        copyrights = sorted(copyrights)

        logger.debug("found the following copyrights: %s", copyrights)

        for file in licenses:
            if "dist-info" in file:
                license_file = file
        if not license_file:
            license_file = licenses[0]

        with (self.wheel.extract_path / license_file).open() as f:
            for line in f.readlines():
                license_content += " " + line

        if license_content:
            self.dump_template(
                "copyright",
                license=self.license,
                license_content=license_content,
                copyrights=copyrights,
            )
        else:
            logger.warning("license not found !")

        # FIXME: licenses should not be copied by the install script

    def create(self):
        if not self.debian.exists():
            self.debian.mkdir(parents=True)

        for template in [
            "changelog",
            "control",
            "compat",
            "postinst",
            "prerm",
        ]:
            self.dump_template(template)

        self.fix_shebangs()
        self.rules()
        self.install()
        self.copyright()

        # dpkg-shlibdeps won't work without debian/control
        self.search_shlibs_deps()

        # re-generate debian/control with deps found by dpkg-shlibdeps
        self.dump_template("control")

    def dump_template(self, template_name, **kwargs):
        template = environment.get_template(template_name)
        output_path = str(self.debian / template_name)
        template.stream(package=self, ctx=self.ctx, **kwargs).dump(output_path)

    def fix_shebangs(self):
        files = [self.root / self.src / x for x in self.wheel.record.scripts]
        for file in files:
            content = file.read_text()
            shebang = "#!/usr/bin/env python%s" % self.ctx.python_version.major
            if not content.startswith(shebang):
                content = content.split("\n")
                content[0] = shebang
                content = "\n".join(content)
                with file.open("w") as g:
                    g.write(content)

    def search_shlibs_deps(self):
        """
        Search packages providing shared libs dependencies
        :return: List of packages providing those libs
        """
        shlibdeps = set()
        missing_libs = set()

        if self.wheel.record.lib_dirs:
            args = (
                ["dpkg-shlibdeps"]
                + ["-l" + str(self.src / x) for x in self.wheel.record.lib_dirs]
                + [str(self.src / x) for x in self.wheel.record.libs]
            )
            output, _ = shell(args, cwd=self.root)
            missing_libs.update(DPKG_SHLIBS_RE.findall(output, re.MULTILINE))

        if missing_libs:
            logger.info(
                "dpkg-shlibdeps reported the following missing "
                "shared libs dependencies: %s",
                missing_libs,
            )

            # search packages providing those libs
            for lib in missing_libs:
                output, _ = shell(["apt-file", "search", lib, "-a", self.arch])
                packages = set(APT_FILE_RE.findall(output))

                # remove dbg packages
                packages = [p for p in packages if p[-3:] != "dbg"]

                if not len(packages):
                    logger.warning("did not find a package providing %s", lib)
                else:
                    # we pick the package with the shortest name
                    packages = sorted(packages, key=len)
                    shlibdeps.add(packages[0])

                if len(packages) > 1:
                    logger.warning(
                        f"several packages providing {lib}: {packages}, picking "
                        f"{packages[0]}, edit debian/control to use another one."
                    )

        if shlibdeps:
            logger.info(f"detected dependencies: {shlibdeps}")

        self.depends = list(set(self.depends) | shlibdeps)


def convert_wheels(
    settings: Settings,
    output_directory: Path,
    wheel_paths: List[Path],
) -> List[SourcePackage]:
    if output_directory.exists() is True and output_directory.is_dir() is False:
        logger.error(f"{output_directory} is not a directory")
        return []

    output_directory.mkdir(exist_ok=True, parents=True)

    if wheel_paths:
        logger.task("Unpacking %s wheels", len(wheel_paths))

    wheels = []
    for file in wheel_paths:
        wheel = parse_wheel(file)
        ctx = settings.get_ctx(wheel.wheel_name)

        if not wheel.cpython_supported:
            # ignore wheels that are not cpython compatible
            logger.warning(f"{wheel.wheel_name} does not support cpython")
            continue

        if not wheel.version_supported(ctx.python_version):
            # ignore wheels that are not compatible specified python version
            logger.warning(
                f"{wheel.wheel_name} does not support python {ctx.python_version}"
            )
            continue

        logger.info("%s", wheel.wheel_name)
        wheels.append(wheel)

    packages = []
    for wheel in wheels:
        logger.task(f"Converting wheel {wheel}")
        ctx = settings.get_ctx(wheel.wheel_name)
        package = SourcePackage(ctx, wheel, output_directory, extras=wheels)
        package.create()
        packages.append(package)

    return packages
