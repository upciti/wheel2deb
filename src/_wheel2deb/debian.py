import os
import re
import shutil
import tempfile
from pathlib import Path

from dirsync import sync

from .depends import normalize_package_version, search_python_deps, suggest_name
from .logger import logging
from .templates import environment
from .tools import shell
from .version import __version__

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

    def __init__(self, ctx, wheel, output, extras=None):
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
        self.filename = "%s_%s_%s.deb" % (self.name, version_without_epoch, self.arch)

        # root directory of the debian source package
        self.root = Path(output) / self.filename[:-4]
        # relative path to wheel.extract_path from self.root
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
        self.depends = ["%s:any" % self.interpreter]
        if wheel.version_range(self.pyvers):
            vrange = wheel.version_range(self.pyvers)
            if vrange.max:
                self.depends.append("%s (<< %s)" % (self.interpreter, vrange.max))
            if vrange.min:
                self.depends.append("%s (>= %s~)" % (self.interpreter, vrange.min))

        deps, missing = search_python_deps(ctx, wheel, extras)
        self.depends.extend(deps)
        self.depends.extend(ctx.depends)

        # write unsatisfied requirements in missing.txt
        with open(str(self.root / "missing.txt"), "w") as f:
            f.write("\n".join(missing) + "\n")

        # wheel modules install path
        if self.pyvers.major == 2:
            self.install_path = "/usr/lib/python2.7/dist-packages/"
        else:
            self.install_path = "/usr/lib/python3/dist-packages/"

    def install(self):
        """
        Generate debian/install
        """
        install = set()

        for d in os.listdir(str(self.wheel.extract_path)):
            if not d.endswith(".data"):
                install.add(str(self.src / d) + " " + self.install_path)
            else:
                purelib = self.wheel.extract_path / d / "purelib"
                if purelib.exists():
                    install.add(
                        str(self.src / d / "purelib" / "*") + " " + self.install_path
                    )

        if self.wheel.entrypoints and not self.ctx.ignore_entry_points:
            self.run_install_scripts()
            if (Path(self.root) / "entrypoints").exists():
                install.add("entrypoints/* /usr/bin/")

        for script in self.wheel.record.scripts:
            install.add(str(self.src / script) + " /usr/bin/")

        with (self.debian / "install").open("w") as f:
            f.write("\n".join(install))

    def rules(self):
        """
        Generate debian/rules
        """
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

        copyrights = sorted(list(copyrights))

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
        shlibdeps_file = "shlibdeps.txt"

        if (self.root / shlibdeps_file).exists():
            shlibdeps = set((self.root / shlibdeps_file).read_text().split("\n"))

        if self.wheel.record.lib_dirs and not shlibdeps:
            args = (
                ["dpkg-shlibdeps"]
                + ["-l" + str(self.src / x) for x in self.wheel.record.lib_dirs]
                + [str(self.src / x) for x in self.wheel.record.libs]
            )
            output = shell(args, cwd=self.root)[0]
            missing_libs.update(DPKG_SHLIBS_RE.findall(output, re.MULTILINE))

        if missing_libs:
            logger.info(
                "dpkg-shlibdeps reported the following missing "
                "shared libs dependencies: %s",
                missing_libs,
            )

            # search packages providing those libs
            for lib in missing_libs:
                output = shell(["apt-file", "search", lib, "-a", self.arch])[0]
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
                        "several packages providing %s: %s, picking %s, "
                        "edit debian/control to use another one.",
                        lib,
                        packages,
                        packages[0],
                    )

            with open(str(self.root / shlibdeps_file), "w") as f:
                f.write("\n".join(shlibdeps))

        if shlibdeps:
            logger.info("detected dependencies: %s", shlibdeps)

        self.depends = list(set(self.depends) | shlibdeps)

    def run_install_scripts(self):
        import configparser

        from setuptools.command.install_scripts import install_scripts
        from setuptools.dist import Distribution

        config = configparser.ConfigParser()
        config.read_string(self.wheel.entrypoints)

        entrypoints = {}
        for section in config:
            x = ["%s=%s" % k for k in config.items(section)]
            if x:
                entrypoints[section] = x

        settings = dict(
            name=self.wheel.name,
            entry_points=entrypoints,
            version=self.wheel.version,
        )

        dist = Distribution(settings)
        dist.script_name = "setup.py"
        cmd = install_scripts(dist)
        cmd.install_dir = str((self.root / "entrypoints").absolute())
        bs = cmd.get_finalized_command("build_scripts")
        bs.executable = "/usr/bin/python" + str(self.pyvers.major)
        cmd.ensure_finalized()

        # cmd.run() creates some files that we don't want in python cwd
        oldcwd = os.getcwd()
        tempdir = tempfile.mkdtemp()
        os.chdir(tempdir)
        try:
            cmd.run()
        finally:
            os.chdir(oldcwd)
            shutil.rmtree(tempdir, ignore_errors=True)
