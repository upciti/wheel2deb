import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, List, Optional, Tuple

import click
import typer
from typer.core import TyperGroup

from wheel2deb import logger as logging
from wheel2deb.build import build_all_packages, build_packages
from wheel2deb.context import load_configuration
from wheel2deb.debian import convert_wheels
from wheel2deb.logger import enable_debug
from wheel2deb.version import __version__

logger = logging.getLogger(__name__)


class DefaultCommandGroup(TyperGroup):
    """
    Make it so that calling wheel2deb without a subcommand
    is equivalent to calling the default subcommand.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        self.default_command = "default"
        self.ignore_unknown_options = True
        super().__init__(*args, **kwargs)

    def parse_args(self, ctx: click.Context, args: List[str]) -> List[str]:
        if not args:
            args.insert(0, self.default_command)
        return super().parse_args(ctx, args)

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        if cmd_name.startswith("-") and cmd_name not in self.commands:
            cmd_name = self.default_command
            ctx.default_command = True  # type: ignore
        return super().get_command(ctx, cmd_name)

    def resolve_command(
        self, ctx: click.Context, args: List[str]
    ) -> Tuple[str | None, click.Command | None, List[str]]:
        cmd_name, cmd, args = super().resolve_command(ctx, args)
        if hasattr(ctx, "default_command") and cmd_name:
            args.insert(0, cmd_name)
        return cmd_name, cmd, args


option_verbose: bool = typer.Option(
    False,
    "--verbose",
    "-v",
    envvar="WHEEL2DEB_VERBOSE",
    help="Enable more logs.",
    callback=lambda v: enable_debug(v),
)

option_configuration: Optional[Path] = typer.Option(
    None,
    "--config",
    "-c",
    envvar="WHEEL2DEB_CONFIG",
    help="Path to configuration file.",
)

option_output_directory: Path = typer.Option(
    "output",
    "--output-dir",
    "-o",
    envvar="WHEEL2DEB_OUTPUT_DIR",
    help="Directory where debian source packages are generated and built.",
)

option_include_wheels: Optional[List[str]] = typer.Option(
    None,
    "--include",
    "-i",
    envvar="WHEEL2DEB_INCLUDE_WHEELS",
    help="Only wheels with matching names will be converted",
)

option_exclude_wheels: Optional[List[str]] = typer.Option(
    None,
    "--exclude",
    "-e",
    envvar="WHEEL2DEB_EXCLUDE_WHEELS",
    help="Wheels with matching names will not be converted",
)

option_search_paths: List[Path] = typer.Option(
    [Path(".")],
    "--search-path",
    "-x",
    envvar="WHEEL2DEB_SEARCH_PATHS",
    help="Only blueprints with matching names will be taken into account",
)


option_workers_count: int = typer.Option(
    4,
    "--workers",
    "-w",
    envvar="WHEEL2DEB_WORKERS_COUNT",
    help="Max number of source packages to build in parallel",
)

option_force_build: bool = typer.Option(
    False, "--force", help="Build source package even if .deb already exists"
)

app = typer.Typer(cls=DefaultCommandGroup)


@contextmanager
def print_summary_and_exit():
    start_time = time.monotonic()
    yield
    logger.summary(
        f"\nWarnings: {logging.get_warning_counter()}. "
        f"Errors: {logging.get_error_counter()}. "
        f"Elapsed: {round(time.monotonic() - start_time, 3)}s."
    )
    # the return code is the number of errors
    sys.exit(logging.get_error_counter())


def filter_wheels(
    search_paths: List[Path],
    include_wheels: List[str] | None,
    exclude_wheels: List[str] | None,
) -> List[Path]:
    # list all python wheels in search paths
    files = []
    for path in [Path(path) for path in search_paths]:
        files.extend(path.glob("*.whl"))
    files = sorted(files, key=lambda x: x.name)

    filenames = [f.name for f in files]
    if not include_wheels:
        include_wheels = filenames

    # remove excluded wheels
    if exclude_wheels:
        include_wheels = list(filter(lambda x: x not in exclude_wheels, include_wheels))

    return [file for file in files if file.name in include_wheels]


@app.command(help="Generate and build source packages.")
def default(
    verbose: bool = option_verbose,
    configuration_path: Optional[Path] = option_configuration,
    output_directory: Path = option_output_directory,
    search_paths: List[Path] = option_search_paths,
    include_wheels: Optional[List[str]] = option_include_wheels,
    exclude_wheels: Optional[List[str]] = option_exclude_wheels,
    workers_count: int = option_workers_count,
    force_build: bool = option_force_build,
) -> None:
    with print_summary_and_exit():
        settings = load_configuration(configuration_path)
        wheel_paths = filter_wheels(search_paths, include_wheels, exclude_wheels)
        packages = convert_wheels(settings, output_directory, wheel_paths)
        build_packages([p.root for p in packages], workers_count, force_build)


@app.command(help="Convert wheels in search paths to debian source packages")
def convert(
    verbose: bool = option_verbose,
    configuration_path: Optional[Path] = option_configuration,
    output_directory: Path = option_output_directory,
    search_paths: List[Path] = option_search_paths,
    include_wheels: Optional[List[str]] = option_include_wheels,
    exclude_wheels: Optional[List[str]] = option_exclude_wheels,
) -> None:
    with print_summary_and_exit():
        settings = load_configuration(configuration_path)
        wheel_paths = filter_wheels(search_paths, include_wheels, exclude_wheels)
        convert_wheels(settings, output_directory, wheel_paths)


@app.command(help="Build debian packages from source packages.")
def build(
    verbose: bool = option_verbose,
    output_directory: Path = option_output_directory,
    workers_count: int = option_workers_count,
    force_build: bool = option_force_build,
) -> None:
    with print_summary_and_exit():
        build_all_packages(output_directory, workers_count, force_build)


@app.command(help="Output wheel2deb version.")
def version() -> None:
    typer.echo(__version__)


def main() -> None:
    app()
