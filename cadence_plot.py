#!/usr/bin/env python

import click

from coast_guard import utils
from coast_guard import database
from coast_guard import cli_common

import matplotlib.pyplot as plt


def get_obs_mjds(db, psrs):
    """Get a list of MJDs for the observations of the
        given pulsars.

        Inputs:
            db: A database connection object.
            psrs: A list of pulsar names.

        Outputs:
            obs_mjds: A dictionary of lists of observation MJDs.
    """
    prefnames = [utils.get_prefname(name) for name in psrs]
    with db.transaction() as conn:
        select = db.select([db.obs.c.sourcename,
                            db.obs.c.start_mjd]).\
                    where(db.obs.c.sourcename.in_(prefnames))
        results = conn.execute(select)
        rows = results.fetchall()
        results.close()
    obs_mjds = {}
    for row in rows:
        mjdlist = obs_mjds.setdefault(row['sourcename'], [])
        mjdlist.append(row['start_mjd'])
    return obs_mjds


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.argument('pulsars', nargs=-1, required=True)
@cli_common.standard_options
@cli_common.debug_options
def main(pulsars):
    """Plot cadence of pulsar observations."""
    db = database.Database()
    obs_mjds = get_obs_mjds(db, pulsars)
    mjds = []
    ipsr = []
    psrnames = sorted(obs_mjds.keys())
    for ii, psrname in enumerate(psrnames):
        print(psrname, len(obs_mjds[psrname]))
        ipsr.extend([ii]*len(obs_mjds[psrname]))
        mjds.extend(sorted(obs_mjds[psrname]))
    plt.scatter(mjds, ipsr)
    plt.yticks(list(range(len(psrnames))), psrnames)
    plt.xlabel('MJD')
    plt.show()

if __name__ == '__main__':
    main()
