"""
Shared click-based CLI option groups for the CoastGuard command-line
scripts.

This module replaces the old optparse/argparse-based
utils.DefaultOptions/utils.DefaultArguments infrastructure. Those classes
provided a set of reusable option groups ("Standard Options", "Debug
Options", "File Selection Options") that every CoastGuard script's parser
inherited. click has no direct equivalent of subclassing a parser, so the
same behaviour is provided here as a set of *decorators* that can be
stacked onto any click command:

    import click
    from coast_guard import cli_common

    @click.command()
    @click.argument('files', nargs=-1)
    @cli_common.file_selection_options
    @cli_common.standard_options
    @cli_common.debug_options
    def main(files, from_glob, excluded_files, excluded_by_glob):
        infiles = cli_common.resolve_file_list(files, from_glob,
                                                excluded_files, excluded_by_glob)
        ...

Each of the option-group decorators mutates the shared 'config' module as
a side effect, exactly like the callbacks/Actions they replace -- this
preserves behaviour for the rest of the codebase (utils.print_info(),
utils.print_debug(), utils.set_warning_mode(), etc.) which reads its
settings from that module.
"""
import glob as _glob

import click

from coast_guard import config


# ---------------------------------------------------------------------
# "Standard Options": verbosity, colourised output, warnings
# ---------------------------------------------------------------------

def _cb_more_verbose(ctx, param, value):
    if value:
        config.verbosity += value


def _cb_less_verbose(ctx, param, value):
    if value:
        config.verbosity -= value


def _cb_set_verbosity(ctx, param, value):
    if value is not None:
        config.verbosity = value


def _cb_set_log_verbosity(ctx, param, value):
    if value is not None:
        config.log_verbosity = value


def _cb_toggle_colour(ctx, param, value):
    if value:
        config.colour = not config.colour


def _cb_toggle_exverb(ctx, param, value):
    if value:
        config.excessive_verbosity = not config.excessive_verbosity


def _cb_warning_mode(ctx, param, value):
    # Imported lazily to avoid a circular import (utils imports config,
    # and is a fairly heavy module).
    from coast_guard import utils
    if value is not None:
        utils.set_warning_mode(value)
    return value


def standard_options(func):
    """Attach the 'Standard Options' group (verbosity, colour, warnings)
        to a click command. Mirrors utils.DefaultArguments.add_standard_group()
        / utils.DefaultOptions.add_standard_group().
    """
    func = click.option('-W', '--warning-mode', 'warnmode', type=str,
            default=None, expose_value=False, callback=_cb_warning_mode,
            help="Set a filter that applies to all warnings. The "
                 "behaviour of the filter is determined by the action "
                 "provided. 'error' turns warnings into errors, "
                 "'ignore' causes warnings to be not printed. 'always' "
                 "ensures all warnings are printed. (Default: print the "
                 "first occurrence of each warning.)")(func)
    func = click.option('--toggle-exverb', is_flag=True, default=False,
            expose_value=False, callback=_cb_toggle_exverb,
            help="Toggle excessive verbosity. (Default: excessive "
                 "verbosity is %s)" % ((config.excessive_verbosity and "on") or "off"))(func)
    func = click.option('--toggle-colour', is_flag=True, default=False,
            expose_value=False, callback=_cb_toggle_colour,
            help="Toggle colourised output. (Default: colours are %s)" %
                 ((config.colour and "on") or "off"))(func)
    func = click.option('--set-log-verbosity', type=int, default=None,
            expose_value=False, callback=_cb_set_log_verbosity,
            help="Set verbosity level for logging. (Default: verbosity "
                 "level = %d)." % config.log_verbosity)(func)
    func = click.option('--set-verbosity', type=int, default=None,
            expose_value=False, callback=_cb_set_verbosity,
            help="Set verbosity level. (Default: verbosity level = %d)." %
                 config.verbosity)(func)
    func = click.option('-q', '--less-verbose', count=True,
            expose_value=False, callback=_cb_less_verbose,
            help="Be less verbose. Can be given multiple times. "
                 "(Default: verbosity level = %d)." % config.verbosity)(func)
    func = click.option('-v', '--more-verbose', count=True,
            expose_value=False, callback=_cb_more_verbose,
            help="Be more verbose. Can be given multiple times. "
                 "(Default: verbosity level = %d)." % config.verbosity)(func)
    return func


# ---------------------------------------------------------------------
# "Debug Options"
# ---------------------------------------------------------------------

def _cb_list_debug_modes(ctx, param, value):
    if value:
        click.echo("Available debugging modes:")
        for name, desc in config.debug.modes:
            if desc is None:
                continue
            click.echo("    %s: %s" % (name, desc))
        ctx.exit(1)


def _cb_debug_all(ctx, param, value):
    if value:
        config.debug.set_allmodes_on()


def _cb_set_debug_mode(ctx, param, value):
    for mode in value:
        config.debug.set_mode_on(mode)


def _cb_toggle_helpful_debug(ctx, param, value):
    if value:
        config.helpful_debugging = not config.helpful_debugging


def debug_options(func):
    """Attach the 'Debug Options' group to a click command. Mirrors
        utils.DefaultArguments.add_debug_group() /
        utils.DefaultOptions.add_debug_group().
    """
    func = click.option('--toggle-helpful-debug', is_flag=True, default=False,
            expose_value=False, callback=_cb_toggle_helpful_debug,
            help="Toggle helpful debugging. (Default: helpful debugging "
                 "is %s)" % ((config.helpful_debugging and "on") or "off"))(func)
    func = click.option('--list-debug-modes', is_flag=True, default=False,
            expose_value=False, is_eager=True, callback=_cb_list_debug_modes,
            help="List available debugging modes and descriptions, then exit.")(func)
    func = click.option('--set-debug-mode', 'debug_modes', multiple=True,
            default=(), expose_value=False, callback=_cb_set_debug_mode,
            help="Turn on specified debugging mode. Use --list-debug-modes "
                 "to see the list of available modes and descriptions. Can "
                 "be given multiple times. (Default: all debugging modes "
                 "are off)")(func)
    func = click.option('--debug-all', '-d', '--debug', 'debug_all',
            is_flag=True, default=False, expose_value=False,
            callback=_cb_debug_all,
            help="Turn on all debugging modes. (Same as -d/--debug).")(func)
    return func


# ---------------------------------------------------------------------
# "File Selection Options"
# ---------------------------------------------------------------------

def _cb_glob(ctx, param, value):
    matches = []
    for pattern in value:
        matches.extend(_glob.glob(pattern))
    return matches


def file_selection_options(func):
    """Attach the 'File Selection Options' group to a click command,
        exposing 'from_glob', 'excluded_files' and 'excluded_by_glob'
        as keyword arguments. Mirrors
        utils.DefaultArguments.add_file_selection_group().

        Use resolve_file_list() to combine these with a command's
        positional FILES argument into the final list of files to
        process.
    """
    func = click.option('--exclude-glob', 'excluded_by_glob', type=str,
            multiple=True, callback=_cb_glob, default=(),
            help="Glob expression of files to exclude as input. Glob "
                 "expression should be properly quoted to not be expanded "
                 "by the shell prematurely. Can be given multiple times. "
                 "(Default: exclude no files.)")(func)
    func = click.option('-x', '--exclude-file', 'excluded_files', type=str,
            multiple=True, default=(),
            help="Exclude a single file. Multiple -x/--exclude-file "
                 "options can be provided. (Default: don't exclude any "
                 "files.)")(func)
    func = click.option('-g', '--glob', 'from_glob', type=str,
            multiple=True, callback=_cb_glob, default=(),
            help="Glob expression of input files. Glob expression should "
                 "be properly quoted to not be expanded by the shell "
                 "prematurely. Can be given multiple times. (Default: no "
                 "glob expression is used.)")(func)
    return func


def resolve_file_list(files, from_glob=(), excluded_files=(), excluded_by_glob=()):
    """Combine a positional FILES argument with the values produced by
        file_selection_options() into the final ordered, de-duplicated
        list of files to process, honouring exclusions. Mirrors the
        'file_list'/'to_exclude'/'to_clean' logic that used to live in
        each script's main().

        Inputs:
            files: Sequence of files given positionally on the command line.
            from_glob: Sequence of files matched by -g/--glob (already
                globbed by file_selection_options()'s callback).
            excluded_files: Sequence of files given via -x/--exclude-file.
            excluded_by_glob: Sequence of files matched by --exclude-glob
                (already globbed).

        Output:
            infiles: The final list of files to process.
    """
    from coast_guard import utils
    file_list = list(files) + list(from_glob)
    to_exclude = list(excluded_files) + list(excluded_by_glob)
    return utils.exclude_files(file_list, to_exclude)


def common_options(func):
    """Convenience decorator that stacks standard_options + debug_options
        (but not file_selection_options, which not every script needs).
    """
    func = debug_options(func)
    func = standard_options(func)
    return func
