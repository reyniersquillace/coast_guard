#!/usr/bin/env python

import click

from coast_guard import calibrate
from coast_guard import database
from coast_guard import utils
from coast_guard import cli_common


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.option("-n", "--sourcename", "sourcename", type=str,
                help="Name of source for which to update calibrator database.")
@cli_common.standard_options
@cli_common.debug_options
def main(sourcename):
    """Forcefully update calibrator database for a given source."""
    db = database.Database()
    caldbfn = calibrate.update_caldb(db, sourcename, force=True)
    print("Updated %s" % caldbfn)


if __name__ == '__main__':
    main()
