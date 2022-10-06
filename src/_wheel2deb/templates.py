from typing import Optional

from jinja2 import Environment, FunctionLoader

DEBIAN_CHANGELOG = """\
{{ package.name }} ({{ package.version }}) stable; urgency=medium

  * Release {{ package.version }}

 -- {{ ctx.maintainer_name }} <{{ ctx.maintainer_email }}>  Tue, 07 May 2019 20:31:30 +0000
"""

DEBIAN_COMPAT = """\
10
"""

DEBIAN_CONTROL = """\
Source: {{ package.name }}
Priority: optional
Maintainer: ops2deb <ops2deb@upciti.com>
Build-Depends: debhelper{%- if package.build_depends %}, {{ package.build_depends|sort|join(', ') }}{% endif %}
Standards-Version: 3.9.6
{%- if package.homepage %}{{ '\n' }}Homepage: {{ package.homepage }}{% endif %}

Package: {{ package.name }}
Architecture: {{ package.arch }}
{%- if package.provides %}{{ '\n' }}Provides: {{ package.provides|sort|join(', ') }}{% endif %}
{%- if package.depends %}{{ '\n' }}Depends: {{ package.depends|sort|join(', ') }}{% endif %}
{%- if package.recommends %}{{ '\n' }}Recommends: {{ package.recommends|sort|join(', ') }}{% endif %}
{%- if package.replaces %}{{ '\n' }}Replaces: {{ package.replaces|sort|join(', ') }}{% endif %}
{%- if package.conflicts %}{{ '\n' }}Conflicts: {{ package.conflicts|sort|join(', ') }}{% endif %}
Description: {{ package.summary }}
{% if package.description %}{% for line in package.description.split('\n') %} {{ line or '.' }}{{ '\n' if not loop.last else '' }}{% endfor %}{% endif %}

"""

DEBIAN_POSTINST = """\
#!/bin/sh
set -e

#WHEEL2DEB#

{% if package.pyvers.major == 2 %}
{% set pycompile = 'pycompile' %}
{% else %}
{% set pycompile = 'py3compile' %}
{% endif %}

if which {{ pycompile }} >/dev/null 2>&1; then
    {{ pycompile }} -p {{ package.name }}
fi

#DEBHELPER#
"""

DEBIAN_PRERM = """\
#!/bin/sh
set -e

#WHEEL2DEB#

{% if package.pyvers.major == 2 %}
{% set pyclean = 'pyclean' %}
{% else %}
{% set pyclean = 'py3clean' %}
{% endif %}

if which {{ pyclean }} >/dev/null 2>&1; then
    {{ pyclean }} -p {{ package.name }}
fi

#DEBHELPER#
"""

DEBIAN_COPYRIGHT = """\
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/

Files: *
Copyright: {{ copyrights|join('\n           ') }}
License: {{ license }}

License: {{ license }}
{{ license_content }}
"""

DEBIAN_RULES = """\
#!/usr/bin/make -f

%:
	dh $@

override_dh_shlibdeps:
	true

"""


def template_loader(name: str) -> Optional[str]:
    variable_name = f"DEBIAN_{name.upper().replace('-', '_')}"
    template_content: str = globals()[variable_name]
    if variable_name in globals():
        return template_content
    return None


environment = Environment(loader=FunctionLoader(template_loader))
