#!/usr/bin/env python
import matplotlib
matplotlib.use('agg') # A non-interactive backend

import click

from coast_guard import utils
from coast_guard import diagnose
from coast_guard import cli_common


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.argument('files', nargs=-1)
@click.option('-o', 'outpsfn', type=str, default=None,
              help="Output postscript file name. (Default: <archive name>.ps")
@cli_common.standard_options
@cli_common.debug_options
def main(files, outpsfn):
    for arfn in files:
        print("Plotting %s" % arfn, end=' ')
        arf = utils.ArchiveFile(arfn)
        diagnose.make_composite_summary_plot(arf, outpsfn)
        print(" Done")


if __name__ == '__main__':
    main()
