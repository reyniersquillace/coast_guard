#!/usr/bin/env python
import click

from coast_guard import database
from coast_guard import utils
from coast_guard import config
from coast_guard import cli_common


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@cli_common.standard_options
@cli_common.debug_options
def main():
    """Create database tables."""
    engine = database.get_engine(config.dburl)
    database.schema.metadata.create_all(engine)
            # Add this argument to "create_all" to make specific tables:
            # tables=[database.schema.metadata.tables['qctrl'], database.schema.metadata.tables['reattempts']]


if __name__=='__main__':
    main()
