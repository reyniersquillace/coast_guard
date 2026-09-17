#!/usr/bin/env python
"""
make_template.py

Make a template using paas and load it into the database.

Patrick Lazarus, Mar 14, 2014
"""

import os
import shutil
import tempfile

import click

from coast_guard import config
from coast_guard import utils
from coast_guard import list_files
from coast_guard import errors
from coast_guard import cli_common


def get_files_to_combine(rows, max_span=1, min_snr=0):
    """Given a list of result sets from the database return a list of
        filenames to combine to make a template.

        Inputs:
            rows: A list of database result sets as returned by
                'get_files()'.
            max_span: The maximum allowable span, in days, from the 
                first data file to the last data file to combine. 
                (Default: 1 day)
            min_snr: Ignore data files with SNR lower than this value.
                (Default: 0)

        Output:
            files: A list of file names to combine.
    """
    utils.sort_by_keys(rows, ['start_mjd'])
    info = []
    for ii, row in enumerate(rows):
        jj = ii
        tot = 0
        for jj in range(ii, len(rows)):
            if (rows[jj]['start_mjd']-row['start_mjd']) > max_span:
                break
            snr = (rows[jj]['snr'] or 0)  # This will replace None values with 0
            if snr >= min_snr:
                tot += snr
            jj += 1
        info.append((ii, tot, jj-ii))
    if not info:
        return []
    ind, snr, nn = max(info, key=lambda aa: aa[1])
    utils.print_info("Highest total SNR is %g for %d files starting "
                     "at index %d." % (snr, nn, ind), 2)
    touse = rows[ind:ind+nn]
    utils.sort_by_keys(touse, ['snr_r'])
    return [os.path.join(rr['filepath'], rr['filename']) 
            for rr in touse if (rr['snr'] or 0) >= min_snr]


def combine_files(rawfns):
    """Combine raw data files using psradd. The files are
        blindly combined.

        Intput:
            rawfns: A list of data files to combine.

        Output:
            cmbfn: The path to the combined fully scrunched file.
    """
    tmpfile, tmpfn = tempfile.mkstemp(suffix='.cmb', 
                                      dir=config.tmp_directory)
    os.close(tmpfile)
    
    cmd = ['psradd', '-F', '-ip', '-P', '-j', 'DTFp', '-T', '-o', tmpfn] + rawfns
    utils.execute(cmd)
    return tmpfn


def make_template(outdir, psrname, stage, rcvr, max_span=1, min_snr=0):
    if os.path.isdir(outdir):
        outdir = outdir
    else:
        raise errors.InputError("Output directory (%s) doesn't exist!" %
                                outdir)
    filerows = list_files.get_files([psrname], stage, rcvr)
    print("Found %d matching files" % len(filerows))
    fns = get_files_to_combine(filerows, max_span, min_snr)
    if not fns:
        raise errors.TemplateGenerationError("No files for type=%s, "
                                             "psr=%s, rcvr=%s" %
                                             (stage, psrname, rcvr))
    print("Combining %d files" % len(fns))
    cmbfn = combine_files(fns)

    runpaas = True
    tmpdir = tempfile.mkdtemp(suffix="cg_paas", dir=config.tmp_directory)
    while runpaas:
        try:
            print("Running paas")
            utils.execute(['paas', '-D', '-i', cmbfn], dir=tmpdir)
        except:
            if input("Failure! Give up? (y/n): ").lower()[0] == 'y':
                runpaas = False
        else:
            if input("Success! Keep template? (y/n): ").lower()[0] == 'y':
                runpaas = False
                outbasenm = os.path.join(outdir,
                                         "%s_%s_%s" % (psrname, rcvr, stage))
                tmpbasenm = os.path.join(tmpdir, 'paas')
                shutil.copy(tmpbasenm+'.m', outbasenm+'.m')
                shutil.copy(tmpbasenm+'.std', outbasenm+'.std')
                shutil.copy(cmbfn, outbasenm+".add")
    # Clean up paas files
    try:
        shutil.rmtree(tmpdir)
    except: pass
    try:
        os.remove(cmbfn)
    except: pass
    return outbasenm+'.std'


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.option('-p', '--psr', 'psr', type=str, required=True,
                help="The pulsar to create a template for.")
@click.option('--rcvr', 'rcvr', type=str, required=True,
                help="The name of the receiver for "
                     "which to make a template.")
@click.option('-C', "--calibrated", 'calibrated', is_flag=True,
                help="Make template from calibrated pulsar observations.")
@click.option("-m", "--min-snr", 'min_snr', type=float, default=0,
                help="Minimum archive SNR to consider when "
                     "adding data files. (Default: no minimum)")
@click.option("-g", "--max-span", 'max_span', type=float, default=1,
                help="Maximum span, in days, between observations when "
                     "adding data files. (Default: 1 day)")
@click.option("-o", "--output-dir", 'outdir', type=str,
                help="Output directory. (Default: current directory)")
@cli_common.standard_options
@cli_common.debug_options
def main(psr, rcvr, calibrated, min_snr, max_span, outdir):
    """Combine multiple files close in MJD to create a high-SNR
        profile to generate a template using paas
    """
    if outdir is None:
        outdir = os.getcwd()
    stage = 'calibrated' if calibrated else 'cleaned'
    psrname = utils.get_prefname(psr)
    stdfn = make_template(outdir, psrname, stage, rcvr,
                          max_span, min_snr)
    print("Made template: %s", stdfn)


if __name__ == '__main__':
    main()
