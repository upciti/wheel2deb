import re
from packaging.version import parse

from .logger import logging
from .apt import search_packages

logger = logging.getLogger(__name__)

APT_FILE_RE = re.compile(r"(.*lib.+):\s(?:/usr/lib/|/lib/)")

DEB_VERS_OPS = {
    "==": ">=",
    "<": "<<",
    ">": ">>",
    "~=": ">=",
}


def normalize_package_version(python_package_version, prerelease_workaround=True):
    """
    Normalize Python package version to be used as Debian package version.
    :param python_package_version: The version of a Python package (a string).
    :param prerelease_workaround: :data:`True` to enable the pre-release
                                  handling documented below, :data:`False` to
                                  restore the old behavior.
    Reformats Python package versions to comply with the Debian policy manual.
    All characters except alphanumerics, dot (``.``) and plus (``+``) are
    replaced with dashes (``-``).
    The PEP 440 pre-release identifiers 'a', 'b', 'c' and 'rc' are prefixed by
    a tilde (``~``) to replicate the intended ordering in Debian versions, also
    the identifier 'c' is translated into 'rc'. Refer to `issue #8
    <https://github.com/paylogic/py2deb/issues/8>`_ for details.
    """
    # Credits to https://github.com/paylogic/py2deb/blob/master/py2deb/utils.py
    # Lowercase and remove invalid characters from the version string.
    # Points (".") are stripped as well, since we end up with a trailing
    # point with versions like "7.*"
    version = (
        re.sub("[^a-z0-9.+]+", "-", python_package_version.lower())
        .strip("-")
        .strip(".")
    )
    if prerelease_workaround:
        # Translate the PEP 440 pre-release identifier 'c' to 'rc'.
        version = re.sub(r"(\d)c(\d)", r"\1rc\2", version)
        # Replicate the intended ordering of PEP 440 pre-release versions (a, b, rc).
        version = re.sub(r"(\d)(a|b|rc)(\d)", r"\1~\2\3", version)
    return version


def suggest_name(ctx, wheel_name):
    """
    Guess Debian package name from a wheel name and a python implementation.
    :param wheel_name: Name of the distribution wheel
    :type wheel_name: str
    :return: Package name
    """

    prefix = {2: "python", 3: "python3"}[ctx.python_version.major]

    if wheel_name in ctx.map:
        return prefix + "-" + ctx.map[wheel_name]

    basename = re.compile("[^A-Za-z0-9.]+").sub("-", wheel_name)
    basename = basename.replace("python-", "")
    basename = basename.replace("-python", "").lower()

    return prefix + "-" + basename


def suggest_names(ctx, wheel_names):
    for wheel_name in wheel_names:
        yield suggest_name(ctx, wheel_name)


def search_python_deps(ctx, wheel, extras=None):
    """
    Search debian python dependencies
    :param wheel: Python wheel to guess dependencies for
    :param extras: List of wheels. Dependencies provided by this list will be
    considered satisfied
    :return: list of debian packages
    """

    extras = extras or []

    # keep only requirements that match the environment
    # https://www.python.org/dev/peps/pep-0508/#environment-markers
    requirements = wheel.requires(
        {
            "platform_machine": ctx.platform_machine,
            "python_version": str(ctx.python_version),
            "extra": ctx.extra,
        }
    )

    # filter out ignored requirements
    def is_required(r):
        if r.name in ctx.ignore_requirements:
            logger.warning("ignoring requirement %s", str(r))
            return False
        else:
            return True

    requirements = list(filter(is_required, requirements))

    # translate requirements to debian package names
    # and search them in apt cache
    debnames = list(suggest_names(ctx, [r.name for r in requirements]))
    results = search_packages(debnames, ctx.arch)

    candidates = {r.name: [] for r in requirements}
    for res, req in zip(results, requirements):
        if res:
            # add debian package to candidates list
            candidates[req.name].append(res)
        for extra in extras:
            if extra.name == req.name and extra.version_supported(ctx.python_version):
                # add extra wheel to candidates list
                candidates[extra.name].append(extra)

    debian_deps = []
    missing_deps = []
    for pdep, req in zip(debnames, requirements):

        def check(x):
            if req.specifier.contains(x.version, prereleases=True):
                logger.info("%s satisfies requirement %s", x, req)
            else:
                logger.warning("%s does not satisfy requirement %s", x, req)
            return ctx.ignore_upstream_versions or req.specifier.contains(
                x.version, prereleases=True
            )

        version = None
        for candidate in candidates[req.name]:
            if check(candidate):
                if (
                    version and parse(candidate.version) < parse(version)
                ) or not version:
                    version = candidate.version

        if not version:
            logger.error("could not find a candidate for requirement %s", req)
            missing_deps.append(str(req))

        if req.name in ctx.ignore_specifiers:
            logger.warning("ignoring specifiers for dependency %s", req.name)
            debian_deps.append(pdep)
        elif not ctx.ignore_upstream_versions and len(req.specifier):
            for specifier in req.specifier:
                dep = get_dependency_string(pdep, specifier.operator, specifier.version)
                if dep is not None:
                    debian_deps.append(dep)
        else:
            debian_deps.append(pdep)

    return debian_deps, missing_deps


def get_dependency_string(package_name, operator, version):
    """
    Gets a dependency string for a package based on an operator and version.
    """
    # != can't be translated to a package relationship in debian...
    if operator != "!=":
        v = normalize_package_version(version)
        if operator == "==":
            parsed = parse(v)
            if len(parsed.release) == 1:
                # For versions of the form "x" or "x.*". This will return "{x+1}.0"
                return "%s (<< %s)" % (package_name, parsed.release[0] + 1)
            elif len(parsed.release) > 1:
                # For version of the form "x.y" or "x.y.z". This will return "x.{y+1}"
                return "%s (<< %s.%s)" % (
                    package_name,
                    parsed.release[0],
                    parsed.release[1] + 1,
                )
        if operator == "<=":
            v += "-+"
        return "%s (%s %s)" % (package_name, _translate_op(operator), v)

    return None


def _translate_op(operator):
    """
    Translate Python version operator into Debian one.
    """
    return DEB_VERS_OPS.get(operator, operator)
