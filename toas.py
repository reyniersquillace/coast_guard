#!/usr/bin/env python
import os
import os.path

import click

from coast_guard import utils
from coast_guard import config
from coast_guard import errors
from coast_guard import cli_common

def get_standard(arf, base_standards_dir=None, analytic=None):
    """Given an archive file name return the name of the 
        standard profile to use for TOA fitting.

        Input:
            arf: An ArchiveFile object for which we want to get a standard.
            base_stddir: The base directory containing standard profiles.
                (Default: Use value from configuration file.)
            analytic: True if an analytic profile should be returned.
                (Default: Use value from configuration file.)

        Output:
            std: The name of the standard profile.
    """
    if base_standards_dir is None:
        base_standards_dir = config.cfg.base_standards_dir
    if analytic is None:
        analytic = config.cfg.analytic

    if analytic:
        fn = utils.get_outfn("%(name)s_%(telescop)s_%(rcvr)s_%(backend)s.m", arf)
    else:
        fn = utils.get_outfn("%(name)s_%(telescop)s_%(rcvr)s_%(backend)s.std", arf)
    fn = fn.capitalize() # J/B should be capitalized, all the rest lower case
    path = os.path.join(base_standards_dir, arf['telescop'].lower(), \
                            arf['rcvr'].lower(), arf['backend'].lower())
    fn = os.path.join(path, fn)

    return fn


def get_toas(arf, stdfn, nsubint=None, nchan=None, makediag=True, \
                method=None, fmt=None):
    """Get TOAs for the given archive file by running 'pat'.
        If no standard profile is given the location of the 
        stardard will be guessed based on header parameters 
        in the archive.

        Inputs:
            arf: The ArchiveFile object to produce TOAs for.
            stdfn: The name of the standard profile to use.
            nsubint: Scrunch archive to this many subints, and 
                produce a TOA for each subint.
            nchan: Scrunch archive to this many channels, and
                produce a TOA for each channel.
            makediag: A boolean value. If True, make diagnostic
                plots by calling 'pat' with the '-t' flag.
            method: The method to be used by 'pat'.
            fmt: The output format of TOAs.

        Output:
            toas: A list of TOA strings.
    """
    if nsubint is None:
        nsubint = config.cfg.ntoa_time
    if nchan is None:
        nchan = config.cfg.ntoa_freq
    if method is None:
        method = config.cfg.toa_method
    if fmt is None:
        fmt = config.cfg.toa_format

    # Prepare most of call to 'pat'
    if stdfn.endswith(".std"):
        patcmd = "pat -s %s -A %s -f %s " % (stdfn, method, fmt)
    elif stdfn.endswith(".m"):
        patcmd = "pat -m %s -A %s -f %s " % (stdfn, method, fmt)
    else:
        raise errors.StandardProfileError("Only standards with filename " \
                            "extensions of '.std' and '.m' are recognized. " \
                            "(Standard provided: %s)" % stdfn)

    if makediag:
        patcmd += "-t "

    basefn = os.path.splitext(arf.fn)[0]
    if nsubint*nchan > 1:
        # If we want to partially scrunch the data call 'pam'
        scrunchedfn = basefn + '.scrn.tmp'
        utils.execute("pam --setnsub %d --setnchn %d -e scrn.tmp %s" % \
                        (nsubint, nchan, arf.fn))
        stdout, stderr = utils.execute(patcmd+"-K %s.toa.png/PNG %s" % \
                                        (basefn, scrunchedfn))
        if not config.debug.INTERMEDIATE:
            os.remove(scrunchedfn)
    else:
        stdout, stderr = utils.execute(patcmd+"-T -F -K %s.toa.png/PNG %s" % \
                                        (basefn, arf.fn))
    
    # Parse output
    outlines = [line.strip() for line in stdout.split('\n') if line.strip()]
    if makediag:
        # Remove line that says plots are being made
        toastrs = outlines[1:]
    else:
        toastrs = outlines

    # Check that we have the right number of TOAs
    if len(toastrs) != nsubint*nchan:
        raise errors.ToaError("Wrong number of TOAs parsed from 'pat' output. " \
                            "Expecting %d. Got %d." % \
                            (nsubint*nchan, len(toastrs)))
    return toastrs


def _cb_override_config(key):
    """click callback factory mirroring utils.DefaultOptions.override_config():
        set a config override to the option's value, unless it wasn't given.
    """
    def cb(ctx, param, value):
        if value is not None:
            config.cfg.set_override_config(key, value)
        return value
    return cb


def _cb_set_override_config(key, val):
    """click callback factory mirroring utils.DefaultOptions.set_override_config()/
        unset_override_config(): set a config override to a fixed value, but
        only if the flag was actually given.
    """
    def cb(ctx, param, value):
        if value:
            config.cfg.set_override_config(key, val)
    return cb


def _cb_add_flags(ctx, param, value):
    """click callback for '-f/--flag': append each given flag onto
        config.cfg.flags, mirroring the optparse 'append' action's effect
        (main() reads TOA flags from config.cfg.flags, not from the option
        directly).
    """
    if value:
        for flagstr in value:
            config.cfg.flags.append(flagstr)


def purge_flags_callback(ctx, param, value):
    if value:
        config.cfg.flags[:] = []


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.argument('files', nargs=-1)
@cli_common.file_selection_options
@click.option('--format', 'toa_format', type=str, default=None,
                callback=_cb_override_config('toa_format'),
                help="The pat-recognized TOA format to use. (Default: %s)" %
                     config.cfg.toa_format)
@click.option('--method', 'toa_method', type=str, default=None,
                callback=_cb_override_config('toa_method'),
                help="The pat-recognized TOA method to use. (Default: %s)" %
                     config.cfg.toa_method)
@click.option('--num-subband', 'ntoa_freq', type=int, default=None,
                callback=_cb_override_config('ntoa_freq'),
                help="Number of subbands to generate TOAs for. "
                     "(Default: %d)" % config.cfg.ntoa_freq)
@click.option('--num-subint', 'ntoa_time', type=int, default=None,
                callback=_cb_override_config('ntoa_time'),
                help="Number of subints to generate TOAs for. "
                     "(Default: %d)" % config.cfg.ntoa_time)
@click.option('--base-std-dir', 'base_standards_dir', type=str, default=None,
                callback=_cb_override_config('base_standards_dir'),
                help="The base directory containing standard profiles. "
                     "(Default: %s)" % config.cfg.base_standards_dir)
@click.option('-t', '--template', 'template', type=str, default=None,
                expose_value=False,
                help="The template to use. This may be "
                    "a standard profile (*.std), or an analytic "
                    "template (*.m). No other filename extensions "
                    "are recognized. (Default: automatically grab "
                    "template for this pulsar, telescope, receiver, "
                    "and backend combination.)")
@click.option('-m', '--use-analytic', 'analytic', is_flag=True, default=False,
                expose_value=False, callback=_cb_set_override_config('analytic', True),
                help="Use an analytic template (*.m). NOTE: This only "
                    "applies if the template is automatically "
                    "fetched. (Default: %s)" %
                    ((config.cfg.analytic and "Use analytic") or
                            "Use standard profile"))
@click.option('-s', '--use-standard', 'use_standard', is_flag=True, default=False,
                expose_value=False, callback=_cb_set_override_config('analytic', False),
                help="Use a stardard profile (*.std). NOTE: This only "
                    "applies if the template is automatically "
                    "fetched. (Default: %s)" %
                    ((config.cfg.analytic and "Use analytic") or
                            "Use standard profile"))
@click.option('-f', '--flag', 'flags', multiple=True, default=(),
                expose_value=False, callback=_cb_add_flags,
                help="Add the following flag to each TOA line. "
                    "Be sure to include both the flag name and value. "
                    "Also, make sure you properly quote your flag+value. "
                    "(Default: '%s')" % "', '".join(config.cfg.flags))
@click.option('--burn-flags', is_flag=True, default=False,
                expose_value=False, callback=purge_flags_callback,
                help="Remove all flags (including those previously "
                        "added on the command line).")
@cli_common.standard_options
@cli_common.debug_options
def main(files, from_glob, excluded_files, excluded_by_glob,
            toa_format, toa_method, ntoa_freq, ntoa_time, base_standards_dir):
    print("")
    print("          toas.py")
    print("     Patrick  Lazarus")
    print("")
    to_time = cli_common.resolve_file_list(files, from_glob,
                                        excluded_files, excluded_by_glob)
    print("Number of input files: %d" % len(to_time))

    to_time = [utils.ArchiveFile(fn) for fn in to_time]

    # Read configurations
    for arf in to_time:
        config.cfg.load_configs_for_archive(arf)
        stdfn = get_standard(arf)
        if not os.path.isfile(stdfn):
            raise errors.StandardProfileError("The standard profile (%s) " \
                                            "cannot be found!" % stdfn)
        toastrs = get_toas(arf, stdfn)
        for toastr in toastrs:
            flagstrs = [utils.get_outfn(flag, arf) for flag in config.cfg.flags]
            if flagstrs:
                toastr = toastr + " " + " ".join(flagstrs)
            print(toastr)


if __name__=="__main__":
    main()
