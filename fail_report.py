#!/usr/bin/env python
import os.path

import click

from coast_guard import database
from coast_guard import reduce_data
from coast_guard import utils
from coast_guard import cli_common

def get_files(db):
    """Get a list of files from the database.

        Input:
            db: A Database object.

        Output:
            rows: A list of file rows.
    """
    with db.transaction() as conn:
        select = db.select([db.files])
        results = conn.execute(select)
        rows = results.fetchall()
        results.close()
    return rows


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.option("-O", "--output-style", "output_style", default="overview",
                help="How to display output. Possible "
                    "values are 'overview' and 'detail'. "
                    "(Default: overview)")
@cli_common.standard_options
@cli_common.debug_options
def main(output_style):
    """Get a report of files that failed the automated Asterix
        data reduction.
    """
    db = database.Database()
    nfailed = {}
    ntotal = {}
    for filerow in get_files(db):
        ntotal[filerow['stage']] = 1 + \
                        ntotal.setdefault(filerow['stage'], 0)
        if filerow['status'] == 'failed':
            nfailed[filerow['stage']] = 1 + \
                            nfailed.setdefault(filerow['stage'], 0)
            if output_style == 'detail':
                logrow = reduce_data.get_log(db, filerow['group_id'])
                print("File ID: %d - Group ID: %d (%s)" % \
                        (filerow['file_id'], filerow['group_id'], \
                                        filerow['stage']))
                print("    %s" % os.path.join(filerow['filepath'], \
                                                filerow['filename']))
                print("    log: %s" % os.path.join(logrow['logpath'], \
                                                    logrow['logname']))
                print("    Note: %s" % filerow['note'])
                print("")
    if output_style == 'overview':
        print("Overview")
        for stage in ('combined', 'corrected', 'cleaned'):
            print("%s: %d failed / %d total" % \
                    (stage.title(), nfailed.get(stage, 0), \
                            ntotal.get(stage, 0)))


if __name__ == '__main__':
    main()
