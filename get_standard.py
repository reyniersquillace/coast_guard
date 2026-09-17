#!/usr/bin/env python
import sys

from coast_guard import utils
from coast_guard import toas

arf = utils.ArchiveFile(sys.argv[1])
print(toas.get_standard(arf, analytic=False))
